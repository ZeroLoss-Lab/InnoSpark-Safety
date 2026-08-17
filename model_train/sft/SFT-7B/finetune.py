
from dataclasses import dataclass, field
import json
import math
import logging
import os
from typing import Dict, Optional, List
import torch
from torch.utils.data import Dataset
# from datasets import Dataset,concatenate_datasets
from deepspeed import zero
from deepspeed.runtime.zero.partition_parameters import ZeroParamStatus
import transformers
from transformers import Trainer, GPTQConfig, deepspeed
from transformers.trainer_pt_utils import LabelSmoother
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from accelerate.utils import DistributedType
import random
import matplotlib.pyplot as plt
current_dir = os.path.dirname(os.path.abspath(__file__))

IGNORE_TOKEN_ID = LabelSmoother.ignore_index


@dataclass
class ModelArguments:
    model_name_or_path: Optional[str] = field(default="Qwen/Qwen-7B")


@dataclass
class DataArguments:
    data_path: str = field(
        default=None, metadata={"help": "Path to the training data."}
    )
    eval_data_path: str = field(
        default=None, metadata={"help": "Path to the evaluation data."}
    )
    lazy_preprocess: bool = False


@dataclass
class TrainingArguments(transformers.TrainingArguments):
    cache_dir: Optional[str] = field(default=None)
    optim: str = field(default="adamw_torch")
    model_max_length: int = field(
        default=8192,
        metadata={
            "help": "Maximum sequence length. Sequences will be right padded (and possibly truncated)."
        },
    )
    use_lora: bool = False


@dataclass
class LoraArguments:
    lora_r: int = 64
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = field(
        # default_factory=lambda: ["c_attn", "c_proj", "w1", "w2"]
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj",'up_proj','down_proj','embed_tokens','lm_head']
    )
    lora_weight_path: str = ""
    lora_bias: str = "none"
    q_lora: bool = False


def maybe_zero_3(param):
    if hasattr(param, "ds_id"):
        assert param.ds_status == ZeroParamStatus.NOT_AVAILABLE
        with zero.GatheredParameters([param]):
            param = param.data.detach().cpu().clone()
    else:
        param = param.detach().cpu().clone()
    return param


# Borrowed from peft.utils.get_peft_model_state_dict
def get_peft_state_maybe_zero_3(named_params, bias):
    if bias == "none":
        to_return = {k: t for k, t in named_params if "lora_" in k}
    elif bias == "all":
        to_return = {k: t for k, t in named_params if "lora_" in k or "bias" in k}
    elif bias == "lora_only":
        to_return = {}
        maybe_lora_bias = {}
        lora_bias_names = set()
        for k, t in named_params:
            if "lora_" in k:
                to_return[k] = t
                bias_name = k.split("lora_")[0] + "bias"
                lora_bias_names.add(bias_name)
            elif "bias" in k:
                maybe_lora_bias[k] = t
        for k, t in maybe_lora_bias:
            if bias_name in lora_bias_names:
                to_return[bias_name] = t
    else:
        raise NotImplementedError
    to_return = {k: maybe_zero_3(v) for k, v in to_return.items()}
    return to_return


local_rank = None

def rank0_print(*args):
    if local_rank == 0:
        print(*args)


def safe_save_model_for_hf_trainer(trainer: transformers.Trainer, output_dir: str, bias="none"):
    """Collects the state dict and dump to disk."""
    # check if zero3 mode enabled
    if deepspeed.is_deepspeed_zero3_enabled():
        state_dict = trainer.model_wrapped._zero3_consolidated_16bit_state_dict()
    else:
        if trainer.args.use_lora:
            state_dict = get_peft_state_maybe_zero_3(
                trainer.model.named_parameters(), bias
            )
        else:
            state_dict = trainer.model.state_dict()
    if trainer.args.should_save and trainer.args.local_rank == 0:
        trainer._save(output_dir, state_dict=state_dict)

def print_tokens_labels(tokens: List[int], target: List[int], tokenizer):
    # print("Sanity Check >>>>>>>>>>>>>")
    import copy
    temp_tokens=copy.deepcopy(tokens[0].tolist())
    temp_target=copy.deepcopy(target[0].tolist())
    save_name='check_token_target.txt'
    # if os.path.exists(save_name):
    #     os.remove(save_name)
    ff = open(save_name,'a+')
    for t, m in zip(temp_tokens, temp_target):
        if t<0:
            decoded='<Image Data>'
        else:
            decoded = tokenizer.batch_decode([t], skip_special_tokens=False)[0]
        # print("%20s: %6d -> %6d" % (repr(decoded), t, m))
        ff.write("%20s: %6d -> %6d\n" % (repr(decoded), t, m))
    ff.close()
    # print("<<<<<<<<<<<<< Sanity Check")
    assert len(tokens) == len(target), f"length mismatch: {len(tokens)} vs {len(target)}"


def mask_user_targets(input_ids):
    target_batch = []

    for ids in input_ids:
        targets = ids.clone()
        mask_indices = []

        # 找到所有 151644 的位置
        cond = (ids[:-1] == 151644) & (ids[1:] != 77960)
        matched_idx = torch.where(cond)[0]

        im_round = 0
        id_im_start = 0

        for i in matched_idx.tolist():
            im_round += 1
            if im_round == 2:
                id_im_start = 0
                mask_indices.extend(range(id_im_start, i + 3))
                id_im_start = i
            elif im_round % 2 == 0:
                id_im_start = i
            elif im_round % 2 == 1:
                mask_indices.extend(range(id_im_start, min(i + 3, len(ids))))

        if mask_indices:
            targets[mask_indices] = -100

        target_batch.append(targets.unsqueeze(0))

    return torch.cat(target_batch, dim=0)

def preprocess(
    sources,
    tokenizer: transformers.PreTrainedTokenizer,
    max_len: int,
    system_message: str = "You are a helpful assistant."
) -> Dict:
    sources=sources
    input_ids, targets, attention_masks = [], [], []
    TEMPLATE= "{% for message in messages %}{% if loop.first and messages[0]['role'] != 'system' %}{{ '<|im_start|>system\nYou are InnoSpark, created by Lab of AI Education. You are from East China Normal University(华东师范大学), and your Chinese Name is 启创. You are a helpful assistant. <|im_end|>\n' }}{% endif %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"
    from tqdm import tqdm

    # for i, source in enumerate(tqdm(sources["sources"], desc="Processing sources", unit="source")): 
    for source in sources:
        text = tokenizer.apply_chat_template(
            source,
            chat_template=TEMPLATE,
            tokenize=False,
            add_generation_prompt=False,
            padding="max_length",
            max_length=max_len,
            truncation=True,
        )
        part_tokens = tokenizer(
            text,
            return_tensors='pt',
            truncation=True
        )
        
        input_id = part_tokens.input_ids
        attention_mask = part_tokens.attention_mask
        
        target = mask_user_targets(input_id)
        
        pad_input = torch.tensor([151643],device=input_id.device,dtype=input_id.dtype)
        pad_mask = torch.tensor([0],device=input_id.device,dtype=attention_mask.dtype)
        pad_target = torch.tensor([151643],device=input_id.device,dtype=input_id.dtype)
        
        input_id = torch.cat([input_id[0,],pad_input])
        attention_mask = torch.cat([attention_mask[0,],pad_mask])
        target = torch.cat([target[0,],pad_target])
                    
        assert len(input_id) == len(target)
        
        input_ids.append(input_id[:max_len])
        attention_masks.append(attention_mask[:max_len])
        targets.append(target[:max_len])
        # if local_rank==0:
        #     print_tokens_labels(input_id, target, tokenizer)
        # 1/0

    # input_ids=torch.stack(input_ids, dim=0)
    # attention_masks=torch.stack(attention_masks, dim=0)
    # targets=torch.stack(targets, dim=0)

    # if len(input_ids) == 1:
    #     input_ids = input_ids[0]
    # else:
    #     input_ids = torch.tensor(input_ids, dtype=torch.int)
    
    # if len(attention_masks) == 1:
    #     attention_masks = attention_masks[0]
    # else:
    #     attention_masks = torch.tensor(attention_masks, dtype=torch.int)

    # if len(targets) == 1:
    #     targets = targets[0]
    # else:
    #     targets = torch.tensor(targets, dtype=torch.int)
    
    # device = torch.device(f"cuda:{torch.cuda.current_device()}")

    # input_ids.to(device)
    # attention_masks.to(device)
    # targets.to(device)

    # print(device)

    # print(input_ids.device)
    # print(attention_masks.device)
    # print(targets.device)
        # 
        # 1/0
    # print(len(input_ids))
    # print(type(input_ids[0]))
    # print(input_ids[0].shape)
    # input_ids = torch.tensor(input_ids, dtype=torch.int)
    # targets = torch.tensor(targets, dtype=torch.int)

        

    # roles = {"user": "<|im_start|>user", "assistant": "<|im_start|>assistant"}
    # roles = {"user": "<|im_start|>user", "assistant": "<|im_start|>assistant", "observation": "<|im_start|>observation"}

    # im_start = tokenizer.im_start_id
    # im_end = tokenizer.im_end_id
    # nl_tokens = tokenizer('\n').input_ids
    # _system = tokenizer('system').input_ids + nl_tokens
    # _user = tokenizer('user').input_ids + nl_tokens
    # _observation = tokenizer('observation').input_ids + nl_tokens
    # _assistant = tokenizer('assistant').input_ids + nl_tokens

    # # Apply prompt templates
    # input_ids, targets = [], []
    # for i, source in enumerate(sources):
    #     # if roles[source[0]["role"]] != roles["user"]:
    #     #     source = source[1:]

    #     input_id, target = [], []
    #     system = [im_start] + _system + tokenizer(system_message).input_ids + [im_end] + nl_tokens
    #     input_id += system
    #     target += [im_start] + [IGNORE_TOKEN_ID] * (len(system)-3) + [im_end] + nl_tokens
    #     assert len(input_id) == len(target)
    #     for j, sentence in enumerate(source):
    #         role = roles[sentence["from"]]
    #         _input_id = tokenizer(role).input_ids + nl_tokens + \
    #             tokenizer(sentence["value"]).input_ids + [im_end] + nl_tokens
    #         input_id += _input_id
    #         if role == '<|im_start|>user' or role == "<|im_start|>observation":
    #             _target = [im_start] + [IGNORE_TOKEN_ID] * (len(_input_id)-3) + [im_end] + nl_tokens
    #         elif role == '<|im_start|>assistant':
    #             _target = [im_start] + [IGNORE_TOKEN_ID] * len(tokenizer(role).input_ids) + \
    #                 _input_id[len(tokenizer(role).input_ids)+1:-2] + [im_end] + nl_tokens
    #         else:
    #             raise NotImplementedError
    #         target += _target
    #     assert len(input_id) == len(target)
    #     input_id += [tokenizer.pad_token_id] * (max_len - len(input_id))
    #     target += [IGNORE_TOKEN_ID] * (max_len - len(target))
    #     input_ids.append(input_id[:max_len])
    #     targets.append(target[:max_len])
    # input_ids = torch.tensor(input_ids, dtype=torch.int)
    # targets = torch.tensor(targets, dtype=torch.int)

    return dict(
        input_ids=input_ids,
        labels=targets,
        attention_mask=attention_masks, #input_ids.ne(tokenizer.pad_token_id)
    )

def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except json.JSONDecodeError:
        print(f"File {file_path} is not a valid JSON file.")
    except Exception as e:
        print(f"An error occurred: {e}")

class SupervisedDataset(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, raw_data, tokenizer: transformers.PreTrainedTokenizer, max_len: int):
        super(SupervisedDataset, self).__init__()

        rank0_print("Formatting inputs...")
        sources = [example for example in raw_data]
        data_dict = preprocess(sources, tokenizer, max_len)

        self.input_ids = data_dict["input_ids"]
        self.labels = data_dict["labels"]
        self.attention_mask = data_dict["attention_mask"]
        self.device=torch.device(f"cuda:{torch.cuda.current_device()}")

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        # print(self.input_ids[i].shape)
        return dict(
            input_ids=self.input_ids[i].to(self.device),
            labels=self.labels[i].to(self.device),
            attention_mask=self.attention_mask[i].to(self.device),
        )


class LazySupervisedDataset(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, raw_data, tokenizer: transformers.PreTrainedTokenizer, max_len: int):
        super(LazySupervisedDataset, self).__init__()
        self.tokenizer = tokenizer
        self.max_len = max_len

        rank0_print("Formatting inputs...Skip in lazy mode")
        self.tokenizer = tokenizer
        self.raw_data = raw_data
        # self.cached_data_dict = {}

    def __len__(self):
        return len(self.raw_data)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        # if i in self.cached_data_dict:
        #     return self.cached_data_dict[i]

        ret = preprocess([self.raw_data[i]], self.tokenizer, self.max_len)
        ret = dict(
            input_ids=ret["input_ids"][0],
            labels=ret["labels"][0],
            attention_mask=ret["attention_mask"][0],
        )
        # self.cached_data_dict[i] = ret

        return ret


class SupervisedDatasetFromPt(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, data_dict, tokenizer: transformers.PreTrainedTokenizer, max_len: int):
        super(SupervisedDatasetFromPt, self).__init__()

        rank0_print("Formatting inputs...")
        # sources = [example for example in raw_data]
        # data_dict = preprocess(sources, tokenizer, max_len)
        
        self.input_ids = data_dict["input_ids"]
        self.labels = data_dict["labels"]
        self.attention_mask = data_dict["attention_mask"]
        self.device=torch.device(f"cuda:{torch.cuda.current_device()}")
        self.max_len = max_len

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, i) -> Dict[str, torch.Tensor]:
        # print(self.input_ids[i].shape)
        return dict(
            input_ids=self.input_ids[i][0][:self.max_len].to(self.device),
            labels=self.labels[i][0][:self.max_len].to(self.device),
            attention_mask=self.attention_mask[i][0][:self.max_len].to(self.device),
        )

def total_content_length(conversation):
    user_content = conversation[0]['content']
    assistant_content = conversation[1]['content']
    return len(user_content) + len(assistant_content)

def make_supervised_data_module(
    tokenizer: transformers.PreTrainedTokenizer, data_args, max_len,
) -> Dict:
    """Make dataset and collator for supervised fine-tuning."""
    # dataset_cls = (
    #     LazySupervisedDataset if data_args.lazy_preprocess else SupervisedDataset
    # )
    # dataset_cls = SupervisedDatasetFromPt
    dataset_cls = LazySupervisedDataset
    rank0_print("Loading data...")

    # train_json = json.load(open(data_args.data_path, "r"))
    dirs = os.listdir(data_args.data_path)
    all_data=[]
    for one in dirs:
        train_json=read_json_file(os.path.join(data_args.data_path,one))
        all_data+=train_json
    all_data = sorted(all_data, key=total_content_length)
    train_dataset = dataset_cls(all_data,tokenizer,max_len)
    
    # random.seed(42)
    # random.shuffle(all_data)
    
    # print(all_data[0])
    # print(f"train_json {len(train_json)}")
    # 1/0
    # all_data = torch.load(data_args.data_path)
    # train_dataset = dataset_cls(all_data, tokenizer=tokenizer, max_len=max_len)
    # del all_data
    # dataset = Dataset.from_dict({'sources':all_data[:int(len(all_data))]})
    # current_columns = dataset.column_names
    # train_dataset = dataset.map(
    #     preprocess, #sft数据
    #     fn_kwargs = {"tokenizer":tokenizer,"max_len":max_len},
    #     batched = True,
    #     batch_size = 1000,
    #     remove_columns=current_columns if current_columns else None,
    #     num_proc=16
    # )

    if data_args.eval_data_path:
        eval_json = json.load(open(data_args.eval_data_path, "r"))
        eval_dataset = dataset_cls(eval_json, tokenizer=tokenizer, max_len=max_len)
    else:
        eval_dataset = None

    return dict(train_dataset=train_dataset, eval_dataset=eval_dataset)


def train():
    global local_rank

    parser = transformers.HfArgumentParser(
        (ModelArguments, DataArguments, TrainingArguments, LoraArguments)
    )
    (
        model_args,
        data_args,
        training_args,
        lora_args,
    ) = parser.parse_args_into_dataclasses()

    # This serves for single-gpu qlora.
    if getattr(training_args, 'deepspeed', None) and int(os.environ.get("WORLD_SIZE", 1))==1:
        training_args.distributed_state.distributed_type = DistributedType.DEEPSPEED

    local_rank = training_args.local_rank

    device_map = None
    world_size = int(os.environ.get("WORLD_SIZE", 1))
    ddp = world_size != 1
    if lora_args.q_lora:
        device_map = {"": int(os.environ.get("LOCAL_RANK") or 0)} if ddp else "auto"
        if len(training_args.fsdp) > 0 or deepspeed.is_deepspeed_zero3_enabled():
            logging.warning(
                "FSDP or ZeRO3 are incompatible with QLoRA."
            )

    is_chat_model = 'chat' in model_args.model_name_or_path.lower()

    # if (
    #         training_args.use_lora
    #         and not lora_args.q_lora
    #         and deepspeed.is_deepspeed_zero3_enabled()
    #         and not is_chat_model
    # ):
    #     raise RuntimeError("ZeRO3 is incompatible with LoRA when finetuning on base model.")

    model_load_kwargs = {
        'low_cpu_mem_usage': not deepspeed.is_deepspeed_zero3_enabled(),
    }

    # Set RoPE scaling factor
    config = transformers.AutoConfig.from_pretrained(
        model_args.model_name_or_path,
        cache_dir=training_args.cache_dir,
        trust_remote_code=True,
    )
    config.use_cache = False
    # Load tokenizer and data
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        cache_dir=training_args.cache_dir,
        model_max_length=training_args.model_max_length,
        padding_side="right",
        use_fast=False,
        trust_remote_code=True,
    )
    # tokenizer.pad_token_id = tokenizer.eod_id
    # Load data
    data_module = make_supervised_data_module(
        tokenizer=tokenizer, data_args=data_args, max_len=training_args.model_max_length
    )

    # Load model
    model = transformers.AutoModelForCausalLM.from_pretrained(
        model_args.model_name_or_path,
        config=config,
        cache_dir=training_args.cache_dir,
        device_map=device_map,
        trust_remote_code=True,
        quantization_config=GPTQConfig(
            bits=4, disable_exllama=True
        )
        if training_args.use_lora and lora_args.q_lora
        else None,
        **model_load_kwargs,
    )

    print(model)

    if training_args.use_lora:
        if lora_args.q_lora or is_chat_model:
            modules_to_save = None
        else:
            modules_to_save = ["wte", "lm_head"]
        lora_config = LoraConfig(
            r=lora_args.lora_r,
            lora_alpha=lora_args.lora_alpha,
            target_modules=lora_args.lora_target_modules,
            lora_dropout=lora_args.lora_dropout,
            bias=lora_args.lora_bias,
            task_type="CAUSAL_LM",
            modules_to_save=modules_to_save  # This argument serves for adding new tokens.
        )
        if lora_args.q_lora:
            model = prepare_model_for_kbit_training(
                model, use_gradient_checkpointing=training_args.gradient_checkpointing
            )

        model = get_peft_model(model, lora_config)

        # Print peft trainable params
        # model.print_trainable_parameters()

        if training_args.gradient_checkpointing:
            model.enable_input_require_grads()

    # print(model)


    # Start trainner
    trainer = Trainer(
        model=model, tokenizer=tokenizer, args=training_args, **data_module
    )

    trainer.train()
    trainer.save_state()

    safe_save_model_for_hf_trainer(trainer=trainer, output_dir=training_args.output_dir, bias=lora_args.lora_bias)
    
    metrics = {
        'train_loss': [log['loss'] for log in trainer.state.log_history if 'loss' in log],
        # 'val_loss': [log['eval_loss'] for log in trainer.state.log_history if 'eval_loss' in log],
        # 'test_loss': [log['test_loss'] for log in trainer.state.log_history if 'test_loss' in log]
    }
    print(metrics)
    train_loss=metrics["train_loss"]
    # val_loss=metrics["val_loss"]
    # test_loss_value=metrics["test_loss"][0]
    epochs = range(1, len(train_loss) + 1)  # 生成对应的epoch编号[1, 2, 3]
    # 创建图像
    plt.figure(figsize=(8, 5))
    plt.plot(epochs, train_loss, 'bo-', label='Train Loss')  # 蓝色圆点实线
    # plt.plot(epochs, val_loss, 'yo-', label='val Loss')  # 蓝色圆点实线
    # plt.plot(epochs, test_loss, 'r--', label='Test Loss') 
    plt.title('Training Loss Curve', fontsize=14)
    plt.xlabel('Epochs', fontsize=12)
    plt.ylabel('Loss Value', fontsize=12)

    plt.grid(True, alpha=0.3)  # 半透明网格线
    plt.legend()
    plt.show()
    plt.savefig(os.path.join(current_dir,"training_loss.png"), dpi=600)
if __name__ == "__main__":
    train()

