## 首先参照data文件中example.json文件，将SFT数据按照json文件中的数据格式处理完成，即可进行SFT训练。

## 使用sft.sh进行SFT训练时，只需要指定几个关键参数：

```
1.MODEL：训练模型的地址

2.DATA：处理后数据的文件夹地址

3.OUTPUT_PATH：模型训练完成后的输出地址

4.DS_CONFIG_PATH：deepspeed的配置文件地址，参考ds_config中的文件

5.model_max_length：训练模型的最大上下文长度

6.gradient_accumulation_steps：模型梯度累计的步数

7.save_steps：模型checkpoint的保存步数

8.export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 指定使用的GPU，这里是单机8卡
```
