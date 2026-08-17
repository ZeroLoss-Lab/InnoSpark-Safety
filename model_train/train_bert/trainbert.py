from transformers import BertTokenizer,BertForSequenceClassification
from datasets import load_dataset,interleave_datasets,DatasetDict
import sys
sys.path.append('')
from FZXFunction import *
import os
current_dir = os.path.dirname(os.path.abspath(__file__))



# 原始模型与输出目录
tokenizer_path = os.getenv("BERT_TOKENIZER_PATH", "bert-base-chinese")
model_save_path = os.getenv("BERT_MODEL_OUTPUT", os.path.join(current_dir, "checkpoint"))
dataset_save_path = os.getenv("BERT_DATASET_CACHE", os.path.join(current_dir, "data"))

tokenizer=BertTokenizer.from_pretrained(tokenizer_path)
# 下载模型到指定路径
# model=BertForSequenceClassification.from_pretrained('bert-base-chinese',num_labels=3)
model = BertForSequenceClassification.from_pretrained(
    tokenizer_path,
    num_labels=3,
    # cache_dir=model_save_path  # 关键参数：指定缓存目录
)

# dataset= load_dataset('lansinuote/ChnSentiCorp')
# huggingface数据集
# dataset = load_dataset(
#     dataset_save_path,
#     # cache_dir=dataset_save_path  # 替换为实际路径
# )

# 自定义数据集
# data_files = {
#     "train": "bert/huggingface/datasets/dataset1/train.jsonl",
#     "validation": "bert/huggingface/datasets/sample/validation.jsonl",
#     "validation": "bert/huggingface/datasets/dataset1/val.jsonl"
# }
# dataset = load_dataset(
#     "json",
#     data_files=data_files
#     # cache_dir=dataset_save_path  # 替换为实际路径
# )

# 交错合并数据集（等概率）
dataset1=load_dataset("json",data_files=os.path.join(current_dir,"data/data+.jsonl"),split="train")
dataset2=load_dataset("json",data_files=os.path.join(current_dir,"data/data-.jsonl"),split="train")
# dataset1=load_json("bert/data_extent/test+.jsonl")
# dataset2=load_json("bert/data_extent/test-.jsonl")
print([dataset1,dataset2])
interleaved_dataset = interleave_datasets(
    [dataset1,dataset2],
    probabilities=[0.5, 0.5],
    # stopping_strategy="first_exhausted"
    stopping_strategy="all_exhausted"
)
dataset = interleaved_dataset.train_test_split(test_size=0.2, seed=42)
val_test = dataset["test"].train_test_split(test_size=0.5, seed=42)
train_set, val_set, test_set = dataset["train"], val_test["train"], val_test["test"]
dataset = DatasetDict({
    "train": train_set,
    "validation": val_set,
    "test": test_set
})
print(dataset)
import re
def clean_text(text):
    text=re.sub(r'^\w\s','',text)
    text=text.strip()
    return text

def tokenize_function(examples):
    return tokenizer(examples['text'],padding='max_length',truncation=True,max_length=256)

encoded_dataset=dataset.map(tokenize_function,batched=True)

from transformers import Trainer,TrainingArguments
training_args=TrainingArguments(
    output_dir=os.path.join(current_dir,'checkpoint'),
    num_train_epochs=5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    # eval_strategy="epoch",
    eval_strategy="steps",
    logging_dir='bert/logs_bert',
    warmup_steps=50, 
)

from sklearn.metrics import accuracy_score

trainer=Trainer(
    model=model,
    args=training_args,
    train_dataset=encoded_dataset['train'],
    eval_dataset=encoded_dataset['validation'],
    
    # compute_metrics=lambda p: {"accuracy":accuracy_score(p.label_ids,preds)}
)
# def compute_metrics(p):
#     preds=p.predictions.argmax(-1)
#     return {"accuracy":accuracy_score(p.label_ids,preds)}
train_losses=[]
val_losses=[]

trainer.train()
trainer.evaluate(encoded_dataset['test'],metric_key_prefix='test')
metrics = {
    'train_loss': [log['loss'] for log in trainer.state.log_history if 'loss' in log],
    'val_loss': [log['eval_loss'] for log in trainer.state.log_history if 'eval_loss' in log],
    'test_loss': [log['test_loss'] for log in trainer.state.log_history if 'test_loss' in log]
}
print(metrics)
train_loss=metrics["train_loss"]
val_loss=metrics["val_loss"]
test_loss_value=metrics["test_loss"][0]
epochs = range(1, len(train_loss) + 1)  # 生成对应的epoch编号[1, 2, 3]
# 创建图像
plt.figure(figsize=(8, 5))
plt.plot(epochs, train_loss, 'bo-', label='Train Loss')  # 蓝色圆点实线
plt.plot(epochs, val_loss, 'yo-', label='val Loss')  # 蓝色圆点实线
# plt.plot(epochs, test_loss, 'r--', label='Test Loss') 
plt.title('Training Loss Curve', fontsize=14)
plt.xlabel('Epochs', fontsize=12)
plt.ylabel('Loss Value', fontsize=12)

plt.grid(True, alpha=0.3)  # 半透明网格线
# 标注测试集损失值
plt.axhline(y=test_loss_value, color='r', linestyle='--', linewidth=1.5, label=f'Test Loss: {test_loss_value:.3f}')

plt.legend()
plt.show()
plt.savefig(os.path.join(current_dir,"training_loss.png"), dpi=600)
# 模型保存
model.save_pretrained(model_save_path)
tokenizer.save_pretrained(model_save_path)


