"""
对话历史管理模块
支持基于session_id的多轮对话管理和用户识别
"""

import json
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from models import ChatMessage


@dataclass
class ConversationTurn:
    """单轮对话"""
    timestamp: str
    request_id: str
    user_message: str
    assistant_response: str
    model: str
    tokens_used: int
    response_time: float
    finish_reason: str


@dataclass
class SessionConversation:
    """会话对话历史"""
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    total_turns: int
    total_tokens: int
    conversation_turns: List[ConversationTurn]


@dataclass
class UserSession:
    """用户会话统计"""
    user_id: str
    total_sessions: int
    total_turns: int
    total_tokens: int
    active_sessions: List[str]
    last_active: str


class ConversationManager:
    """对话历史管理器 - 基于Session，支持异步操作"""
    
    def __init__(self, storage_file: str = "logs/conversations.json", max_history_turns: int = 50):
        self.storage_file = Path(storage_file)
        self.max_history_turns = max_history_turns
        # 存储结构: {session_id: SessionConversation}
        self.sessions: Dict[str, SessionConversation] = {}
        # 用户统计: {user_id: UserSession}
        self.users: Dict[str, UserSession] = {}
        
        # 异步优化相关
        self._save_lock = asyncio.Lock()
        self._pending_saves = False
        self._save_task = None
        
        self.load_conversations()
    
    def load_conversations(self):
        """从文件加载对话历史（启动时同步加载）"""
        try:
            if self.storage_file.exists():
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 加载sessions
                    if 'sessions' in data:
                        for session_id, session_data in data['sessions'].items():
                            turns = [ConversationTurn(**turn) for turn in session_data['conversation_turns']]
                            session_data['conversation_turns'] = turns
                            self.sessions[session_id] = SessionConversation(**session_data)
                    
                    # 加载users统计
                    if 'users' in data:
                        for user_id, user_data in data['users'].items():
                            self.users[user_id] = UserSession(**user_data)
        except Exception as e:
            print(f"加载对话历史失败: {e}")
            self.sessions = {}
            self.users = {}
    
    async def save_conversations_async(self):
        """异步保存对话历史到文件"""
        try:
            # 确保目录存在
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 将对话历史转换为可序列化的格式
            data = {
                'sessions': {},
                'users': {}
            }
            
            for session_id, session in self.sessions.items():
                data['sessions'][session_id] = asdict(session)
            
            for user_id, user in self.users.items():
                data['users'][user_id] = asdict(user)
            
            # 使用线程池执行文件IO以避免阻塞事件循环
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_json_file, data)
        except Exception as e:
            print(f"保存对话历史失败: {e}")
    
    def _write_json_file(self, data):
        """在线程池中执行的文件写入操作"""
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def schedule_save(self):
        """调度延迟保存，批量处理保存请求"""
        if self._pending_saves:
            return  # 已经有保存任务在等待
        
        self._pending_saves = True
        
        # 等待2秒后保存，允许批量处理多个更新
        await asyncio.sleep(2.0)
        
        async with self._save_lock:
            if self._pending_saves:
                await self.save_conversations_async()
                self._pending_saves = False
    
    def save_conversations(self):
        """保存对话历史到文件（向后兼容的同步方法，已优化为非阻塞）"""
        # 创建后台任务来处理保存
        if asyncio.get_event_loop().is_running():
            # 如果在事件循环中，创建后台任务
            asyncio.create_task(self.schedule_save())
        else:
            # 如果不在事件循环中，同步保存
            try:
                self.storage_file.parent.mkdir(parents=True, exist_ok=True)
                data = {
                    'sessions': {session_id: asdict(session) for session_id, session in self.sessions.items()},
                    'users': {user_id: asdict(user) for user_id, user in self.users.items()}
                }
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存对话历史失败: {e}")
    
    def get_or_create_session(self, session_id: str, user_id: str) -> SessionConversation:
        """获取或创建会话对话历史"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionConversation(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.now().isoformat(),
                last_active=datetime.now().isoformat(),
                total_turns=0,
                total_tokens=0,
                conversation_turns=[]
            )
            
            # 更新用户统计
            self._update_user_stats(user_id, session_id)
        
        return self.sessions[session_id]
    
    def _update_user_stats(self, user_id: str, session_id: Optional[str] = None):
        """更新用户统计信息"""
        if user_id not in self.users:
            self.users[user_id] = UserSession(
                user_id=user_id,
                total_sessions=0,
                total_turns=0,
                total_tokens=0,
                active_sessions=[],
                last_active=datetime.now().isoformat()
            )
        
        user = self.users[user_id]
        user.last_active = datetime.now().isoformat()
        
        if session_id is not None and session_id not in user.active_sessions:
            user.active_sessions.append(session_id)
            user.total_sessions += 1

    def add_conversation_turn(
        self,
        session_id: str,
        user_id: str,
        request_id: str,
        user_message: str,
        assistant_response: str,
        model: str,
        tokens_used: int,
        response_time: float,
        finish_reason: str
    ):
        """添加一轮对话到历史记录（非阻塞优化版本）"""
        # 获取或创建会话
        session = self.get_or_create_session(session_id, user_id)
        
        # 创建新的对话轮次
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            request_id=request_id,
            user_message=user_message,
            assistant_response=assistant_response,
            model=model,
            tokens_used=tokens_used,
            response_time=response_time,
            finish_reason=finish_reason
        )
        
        # 添加到会话历史
        session.conversation_turns.append(turn)
        session.total_turns += 1
        session.total_tokens += tokens_used
        session.last_active = datetime.now().isoformat()
        
        # 限制历史轮数
        if len(session.conversation_turns) > self.max_history_turns:
            session.conversation_turns = session.conversation_turns[-self.max_history_turns:]
        
        # 更新用户统计
        if user_id in self.users:
            user = self.users[user_id]
            user.total_turns += 1
            user.total_tokens += tokens_used
            user.last_active = datetime.now().isoformat()
        
        # 非阻塞保存 - 调度延迟保存
        self.save_conversations()
    
    def get_session_history(self, session_id: str, max_turns: int = 10) -> List[ChatMessage]:
        """获取指定session的对话历史，返回消息格式"""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        recent_turns = session.conversation_turns[-max_turns:] if max_turns > 0 else session.conversation_turns
        
        # 转换为消息格式
        messages = []
        for turn in recent_turns:
            # 添加用户消息
            messages.append(ChatMessage(role="user", content=turn.user_message))
            # 添加助手回复
            messages.append(ChatMessage(role="assistant", content=turn.assistant_response))
        
        return messages
    
    def get_session_context(self, session_id: str, user_id: str, new_messages: List[ChatMessage], max_context_turns: int = 5) -> List[ChatMessage]:
        """获取带上下文的完整消息列表"""
        # 确保session存在（即使是空的）
        self.get_or_create_session(session_id, user_id)
        
        # 获取历史对话
        history = self.get_session_history(session_id, max_context_turns)
        
        # 合并历史和新消息
        context_messages = history + new_messages
        
        return context_messages
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        if user_id not in self.users:
            return {
                "user_id": user_id,
                "total_sessions": 0,
                "total_turns": 0,
                "total_tokens": 0,
                "active_sessions": [],
                "last_active": None
            }
        
        user = self.users[user_id]
        return {
            "user_id": user_id,
            "total_sessions": user.total_sessions,
            "total_turns": user.total_turns,
            "total_tokens": user.total_tokens,
            "active_sessions": user.active_sessions,
            "last_active": user.last_active
        }
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        if session_id not in self.sessions:
            return {
                "session_id": session_id,
                "user_id": None,
                "total_turns": 0,
                "total_tokens": 0,
                "created_at": None,
                "last_active": None
            }
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "user_id": session.user_id,
            "total_turns": session.total_turns,
            "total_tokens": session.total_tokens,
            "created_at": session.created_at,
            "last_active": session.last_active,
            "conversation_turns": len(session.conversation_turns)
        }
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户的所有会话ID"""
        if user_id in self.users:
            return self.users[user_id].active_sessions
        return []
    
    def cleanup_old_sessions(self, days: int = 30):
        """清理旧的会话记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        sessions_to_remove = []
        for session_id, session in self.sessions.items():
            try:
                last_active = datetime.fromisoformat(session.last_active)
                if last_active < cutoff_date:
                    sessions_to_remove.append(session_id)
            except ValueError:
                # 如果日期格式有问题，保留对话
                continue
        
        # 清理sessions
        for session_id in sessions_to_remove:
            session = self.sessions[session_id]
            user_id = session.user_id
            
            # 从用户的active_sessions中移除
            if user_id in self.users:
                if session_id in self.users[user_id].active_sessions:
                    self.users[user_id].active_sessions.remove(session_id)
            
            del self.sessions[session_id]
        
        if sessions_to_remove:
            self.save_conversations()
            print(f"清理了 {len(sessions_to_remove)} 个旧会话记录")


# 全局对话管理器实例
conversation_manager = ConversationManager() 