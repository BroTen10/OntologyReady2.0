import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Button, Card, Input, Select, Space, Tag, Typography, message, Divider, Empty,
  Collapse, Spin, Avatar,
} from 'antd';
import {
  SendOutlined, RobotOutlined, UserOutlined, ClearOutlined,
  SettingOutlined, NodeIndexOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';
import * as graphragApi from '../api/graphrag';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

const RETRIEVAL_MODES = [
  { value: 'local', label: '本地检索', desc: '实体邻居扩展' },
  { value: 'global', label: '全局检索', desc: '社区摘要汇总' },
  { value: 'hybrid', label: '混合检索', desc: '本地+全局' },
  { value: 'mixed', label: '组合检索', desc: '混合+朴素' },
  { value: 'naive', label: '朴素检索', desc: '全量实体检索' },
  { value: 'bypass', label: '直接问答', desc: '不使用知识图谱' },
];

export default function GraphRAGQA() {
  const [searchParams] = useSearchParams();
  const wsId = searchParams.get('ws') || '';
  const [workspace, setWorkspace] = useState(null);
  const [mode, setMode] = useState('hybrid');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState('');
  const messagesEndRef = useRef(null);

  const loadWorkspace = useCallback(async () => {
    if (!wsId) return;
    try {
      const res = await graphragApi.getWorkspace(wsId);
      if (res.code === 0) setWorkspace(res.data);
    } catch { /* */ }
  }, [wsId]);

  useEffect(() => { loadWorkspace(); }, [loadWorkspace]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streaming]);

  const handleSend = async () => {
    const q = question.trim();
    if (!q || loading) return;

    setQuestion('');
    const history = messages.slice(-10).map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, { role: 'user', content: q }]);

    setLoading(true);
    setStreaming('');

    try {
      const token = localStorage.getItem('auth_access_token');
      const response = await fetch('/api/graphrag/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ workspace_id: wsId, question: q, history, mode }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            fullContent += data;
            setStreaming(fullContent);
          }
        }
      }

      setMessages((prev) => [...prev, { role: 'assistant', content: fullContent }]);
    } catch {
      message.error('请求失败');
    } finally {
      setLoading(false);
      setStreaming('');
    }
  };

  const handleClear = () => {
    setMessages([]);
    setStreaming('');
  };

  if (!wsId) {
    return (
      <div style={{ padding: 24 }}>
        <Card><Title level={5} type="secondary">请先从知识库页面选择工作空间</Title></Card>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>知识问答</Title>
          {workspace && <Tag color="purple">{workspace.name}</Tag>}
        </Space>
        <Space>
          <Select size="small" value={mode} onChange={setMode} style={{ width: 140 }}
            options={RETRIEVAL_MODES} />
          <Button size="small" icon={<ClearOutlined />} onClick={handleClear}>清空对话</Button>
        </Space>
      </div>

      {/* Mode description */}
      <div style={{ marginBottom: 16 }}>
        <Tag color="blue">{RETRIEVAL_MODES.find((m) => m.value === mode)?.label}</Tag>
        <Text type="secondary" style={{ fontSize: 13 }}>
          {RETRIEVAL_MODES.find((m) => m.value === mode)?.desc}
        </Text>
      </div>

      {/* Chat Area */}
      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column', marginBottom: 16, overflow: 'hidden' }}
        bodyStyle={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', padding: 16 }}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {messages.length === 0 && !streaming && (
            <Empty description="开始提问，探索知识图谱" style={{ marginTop: 60 }}>
              <Text type="secondary">支持 6 种检索模式</Text>
            </Empty>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
              <Avatar icon={m.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                style={{ background: m.role === 'user' ? '#7c3aed' : '#10b981', flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 12, color: '#94a3b8' }}>
                  {m.role === 'user' ? '你' : 'GraphRAG'}
                </Text>
                <div style={{
                  background: m.role === 'user' ? '#f0edff' : '#f8f9fc',
                  borderRadius: 8,
                  padding: '10px 14px',
                  marginTop: 4,
                  whiteSpace: 'pre-wrap',
                  lineHeight: '22px',
                  fontSize: 14,
                }}>
                  {m.content}
                </div>
              </div>
            </div>
          ))}

          {streaming && (
            <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
              <Avatar icon={<RobotOutlined />} style={{ background: '#10b981', flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 12, color: '#94a3b8' }}>GraphRAG</Text>
                <div style={{
                  background: '#f8f9fc', borderRadius: 8, padding: '10px 14px',
                  marginTop: 4, whiteSpace: 'pre-wrap', lineHeight: '22px', fontSize: 14,
                }}>
                  {streaming}
                  <Spin size="small" style={{ marginLeft: 4 }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </Card>

      {/* Input Area */}
      <div style={{ display: 'flex', gap: 12 }}>
        <TextArea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
          placeholder="输入问题，按 Enter 发送，Shift+Enter 换行..."
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={loading}
          style={{ flex: 1 }}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} size="large">
          发送
        </Button>
      </div>
    </div>
  );
}
