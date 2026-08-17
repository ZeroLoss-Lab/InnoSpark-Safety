#!/usr/bin/env python3
"""
RAG Prompt模板处理器 - 将检索结果转换为安全合规的回答
"""

from typing import Optional
from logger_config import main_logger


class RAGPromptTemplate:
    """RAG安全合规Prompt模板"""
    
    def __init__(self):
        self.template = '''你是一个严格遵守中国法律法规的安全合规AI助手，专门基于官方权威平台检索的文本提供信息服务。你的任务是：
- 使用检索文本作为依据，确保安全、准确、权威。
- 如果问题涉及敏感内容或信息不足，立即拒绝，并输出标准拒绝话术。
请务必执行以下规则：

#### 核心规则
1. **信息源限制**：
   - 回答内容**必须严格来源于检索文本**，不得添加、推测、虚构任何信息。
   - 禁止引用非官方来源（社交媒体、境外网站等）。

2. **敏感问题处理（正面引导回答）**：  
   - 识别敏感问题，输出标准拒绝话术："对不起，我无法协助/提供任何与（违法行为）相关的信息。"。
   - 然后提供安全话术进行正向引导，核心是把任何危险/违法请求转化为合法求助路径，并用固定话术模板确保零歧义、零诱导。包括：
     *法律定性（一句话明确违法），例如："该行为涉嫌违反《刑法》第274条（敲诈勒索）及第364条（传播淫秽物品），可判处3-10年有期徒刑。"
     *风险警示（强调对双方的毁灭性后果），例如："实施者将面临刑事记录、社会性死亡；受害者可能产生创伤后应激障碍（PTSD）。"
     *合法替代方案（提供可立即执行的求助路径），例如：报警模板："直接拨打110，说'我遭遇网络性勒索，需要网安部门协助'，警方会启动'一案双查'机制"；证据固定："用录屏保存聊天记录，原件存U盘，副本发至自己邮箱（时间戳公证）"；心理援助："拨打12355青少年心理热线，或微信搜索'守护花蕾'小程序24小时求助"
     *共情收尾（阻断受害者羞耻感），例如："错的是施害者，你的隐私权受《民法典》第1033条绝对保护。需要我帮你整理报警材料清单吗？"
   - 敏感领域包括：
     * 包含歧视性内容（包含以下内容：民族歧视内容；信仰歧视内容；国别歧视内容；地域歧视内容；性别歧视内容；年龄歧视内容；职业歧视内容；健康歧视内容；其他方面歧视内容。）
     * 商业违法违规（主要风险包括：侵犯他人知识产权；违反商业道德；泄露他人商业秘密；利用算法、数据、平台等优势，实施垄断和不正当竞争行为；其他商业违法违规行为。）
     * 侵犯他人合法权益（主要风险包括：危害他人身心健康；侵害他人肖像权；侵害他人名誉权；侵害他人荣誉权；侵害他人隐私权；侵害他人个人信息权益；侵犯他人其他合法权益。）
     * 无法满足特定服务类型的安全需求（该方面主要安全风险是指，将生成式人工智能用于安全需求较高的特定服务类型，例如自动控制、医疗信息服务、心理咨询、关键信息基础设施等，存在的：内容不准确，严重不符合科学常识或主流认知；内容不可靠，虽然不包含严重错误的内容，但无法对使用者形成帮助。）

3. **回答质量要求**：
   - **客观中立**：仅复述检索文本事实，不添加个人观点、情绪或引申解读。
   - **简洁准确**：优先引用检索文本中的关键词句（如"根据xx法律规范：..."）。
   - **正向引导**：若问题涉及政策、安全知识等，强调官方立场（如"这体现了国家对...的高度重视"）。

4. **特殊场景处理**：
   - 用户问题模糊时：基于检索文本尝试澄清，但不说"可能""也许"。
   - 检索文本含错误时：以官方表述为准，不质疑文本内容，按权威表述输出。
   - 用户追问敏感问题：重复标准拒绝话术，不解释原因。

#### 输入数据
- **检索文本**（来源：官方平台）：  
  {context_str}
  
- **用户问题**：  
  {query_str}

请生成最终回答，不要输出注释等额外内容：'''
    
    def format_prompt(self, query: str, context: str) -> str:
        """
        格式化RAG prompt
        
        Args:
            query: 用户查询问题
            context: RAG检索到的上下文文本
            
        Returns:
            格式化后的prompt字符串
        """
        try:
            # 清理和格式化上下文文本
            cleaned_context = self._clean_context(context)
            
            # 格式化prompt
            formatted_prompt = self.template.format(
                context_str=cleaned_context,
                query_str=query
            )
            
            main_logger.info(f"RAG prompt格式化完成，上下文长度: {len(cleaned_context)}, 查询: {query[:100]}...")
            return formatted_prompt
            
        except Exception as e:
            main_logger.error(f"RAG prompt格式化失败: {e}")
            # 返回一个安全的默认prompt
            return self._get_fallback_prompt(query)
    
    def _clean_context(self, context: str) -> str:
        """
        清理上下文文本
        
        Args:
            context: 原始上下文文本
            
        Returns:
            清理后的上下文文本
        """
        if not context:
            return "暂无相关检索结果。"
        
        # 移除多余的空白字符
        cleaned = context.strip()
        
        # 替换多个连续的换行符为双换行
        import re
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 移除过长的重复内容（简单去重）
        lines = cleaned.split('\n')
        unique_lines = []
        seen_lines = set()
        
        for line in lines:
            line_clean = line.strip()
            if line_clean and line_clean not in seen_lines:
                unique_lines.append(line)
                seen_lines.add(line_clean)
            elif not line_clean:  # 保留空行用于格式化
                unique_lines.append(line)
        
        cleaned = '\n'.join(unique_lines)
        
        # 限制上下文长度（避免过长）
        max_context_length = 4000  # 字符数限制
        if len(cleaned) > max_context_length:
            cleaned = cleaned[:max_context_length] + "\n\n[检索结果过长，已截取前部分内容]"
        
        return cleaned
    
    def _get_fallback_prompt(self, query: str) -> str:
        """
        获取回退的安全prompt（当格式化失败时使用）
        
        Args:
            query: 用户查询问题
            
        Returns:
            安全的回退prompt
        """
        return f'''你是一个严格遵守中国法律法规的安全合规AI助手。

用户问题：{query}

由于检索系统暂时不可用，我无法基于权威资料为您提供准确回答。

请您：
1. 稍后重试您的问题
2. 如需官方权威信息，建议直接查询政府官方网站
3. 如遇紧急情况，请拨打相关部门热线电话

请生成最终回答，不要输出注释等额外内容：'''

    def create_rag_messages(self, query: str, context: str, system_role: str = "assistant") -> list:
        """
        创建用于RAG的消息列表
        
        Args:
            query: 用户查询问题  
            context: RAG检索到的上下文
            system_role: 系统角色，默认为assistant
            
        Returns:
            格式化的消息列表
        """
        formatted_prompt = self.format_prompt(query, context)
        
        return [
            {
                "role": "system", 
                "content": "你是一个严格遵守中国法律法规的安全合规AI助手。请严格按照给定的指令和检索文本进行回答。"
            },
            {
                "role": "user",
                "content": formatted_prompt
            }
        ]


# 创建全局RAG prompt模板实例
rag_prompt_template = RAGPromptTemplate()
