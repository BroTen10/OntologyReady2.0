import { useEffect, useRef, useState, useCallback } from 'react';
import {
  Avatar, Button, Card, Collapse, Drawer, Empty, Input, Select,
  Slider, Space, Tag, Typography, message, Spin, Popconfirm, Tooltip,
} from 'antd';
import {
  SendOutlined, RobotOutlined, UserOutlined, ClearOutlined,
  PlusOutlined, DeleteOutlined, SettingOutlined, DatabaseOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useChatStore } from '../stores/chatStore';

const { Text, Title } = Typography;
const { TextArea } = Input;

const DEFAULT_MODEL_PARAMS = {
  temperature: 0.1,
  top_p: 0.3,
  threshold: 0.5,
  top_n: 6,
};

const DEFAULT_SYSTEM_PROMPT = '你是一个基于知识库的问答助手。请严格基于以下上下文回答问题。如果上下文没有相关信息，请明确告知用户。\n\n上下文：\n{{knowledge}}';

export default function RagChat() {
  const {
    conversations, currentConv, messages, streaming, loading, kbs,
    loadKBs, loadConversations, createConversation, selectConversation,
    deleteConversation, sendMessage,
  } = useChatStore();

  const [question, setQuestion] = useState('');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [kbId, setKbId] = useState(null);
  const [modelParams, setModelParams] = useState(DEFAULT_MODEL_PARAMS);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPT);
  const [creating, setCreating] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => { loadKBs(); loadConversations(); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streaming]);

  const handleCreate = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const conv = await createConversation(kbId, '新对话', modelParams, systemPrompt);
      if (!conv) message.error('创建对话失败');
      else setSettingsOpen(false);
    } finally {
      setCreating(false);
    }
  };

  const handleSend = () => {
    const q = question.trim();
    if (!q || loading || !currentConv) return;
    setQuestion('');
    sendMessage(q);
  };

  const handleSelectConv = (convId) => {
    if (currentConv?.conv_id === convId) return;
    selectConversation(convId);
  };

  const citationCount = (msg) => msg.citations?.length || 0;

  return (
    <div style={{ height: '100%', display: 'flex' }}>
      {/* ── Left Sidebar: Conversations ── */}
      <div style={{
        width: 260, borderRight: '1px solid #f0f0f0', display: 'flex',
        flexDirection: 'column', background: '#fafafa',
      }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
          <Button type="primary" icon={<PlusOutlined />} block onClick={() => setSettingsOpen(true)}>
            新建对话
          </Button>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {conversations.length === 0 && (
            <Empty description="暂无对话" style={{ marginTop: 40 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
          {conversations.map((c) => (
            <div
              key={c.conv_id}
              onClick={() => handleSelectConv(c.conv_id)}
              style={{
                padding: '10px 16px', cursor: 'pointer', display: 'flex',
                justifyContent: 'space-between', alignItems: 'center',
                background: currentConv?.conv_id === c.conv_id ? '#e8e0ff' : 'transparent',
                borderLeft: currentConv?.conv_id === c.conv_id ? '3px solid #7c3aed' : '3px solid transparent',
              }}
            >
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <Text style={{ fontSize: 14, display: 'block' }} ellipsis>{c.title || '新对话'}</Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {c.created_at ? new Date(c.created_at).toLocaleDateString() : ''}
                </Text>
              </div>
              <Popconfirm
                title="确认删除该对话？"
                onConfirm={(e) => { e.stopPropagation(); deleteConversation(c.conv_id); }}
                onCancel={(e) => e.stopPropagation()}
              >
                <Button
                  type="text" size="small" danger icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                />
              </Popconfirm>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right Chat Area ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Header */}
        <div style={{
          padding: '12px 24px', borderBottom: '1px solid #f0f0f0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <Space>
            <Title level={5} style={{ margin: 0 }}>{currentConv?.title || '对话助手'}</Title>
            {currentConv?.kb_id && (
              <Tag color="purple" icon={<DatabaseOutlined />}>
                {kbs.find((k) => k.kb_id === currentConv.kb_id)?.name || currentConv.kb_id}
              </Tag>
            )}
          </Space>
          {currentConv && (
            <Button size="small" icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>
              设置
            </Button>
          )}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: 'auto', padding: 24, background: '#fff' }}>
          {!currentConv && (
            <Empty description="选择或创建一个对话开始问答" style={{ marginTop: 80 }}>
              <Text type="secondary">基于知识库的智能对话助手</Text>
            </Empty>
          )}
          {currentConv && messages.length === 0 && !streaming && (
            <Empty description="输入问题，开始对话" style={{ marginTop: 60 }}>
              <Text type="secondary">Enter 发送 / Shift+Enter 换行</Text>
            </Empty>
          )}

          {messages.map((m, i) => (
            <div key={i} style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
              <Avatar
                icon={m.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                style={{ background: m.role === 'user' ? '#7c3aed' : '#10b981', flexShrink: 0 }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text strong style={{ fontSize: 12, color: '#94a3b8' }}>
                  {m.role === 'user' ? '你' : '助手'}
                </Text>
                <div style={{
                  background: m.role === 'user' ? '#f0edff' : '#f8f9fc',
                  borderRadius: 8, padding: '10px 14px', marginTop: 4,
                  whiteSpace: 'pre-wrap', lineHeight: '22px', fontSize: 14,
                }}>
                  {m.content}
                </div>
                {m.role === 'assistant' && citationCount(m) > 0 && (
                  <Collapse
                    size="small"
                    ghost
                    style={{ marginTop: 4 }}
                    items={[{
                      key: 'citations',
                      label: (
                        <Text style={{ fontSize: 12, color: '#7c3aed' }}>
                          <FileTextOutlined /> {citationCount(m)} 个引用来源
                        </Text>
                      ),
                      children: (
                        <div>
                          {m.citations.map((c, ci) => (
                            <div key={ci} style={{
                              padding: '6px 8px', marginTop: 4, background: '#fafafa',
                              borderRadius: 6, borderLeft: '3px solid #7c3aed',
                            }}>
                              <Text style={{ fontSize: 12 }}>
                                <strong>来源 {ci + 1}</strong>
                                {c.filename ? ` — ${c.filename}` : ''}
                                {c.score ? ` (相似度: ${c.score})` : ''}
                              </Text>
                              <Text style={{ fontSize: 12, display: 'block', marginTop: 4 }} ellipsis={{ rows: 3, expandable: true }}>
                                {c.content}
                              </Text>
                            </div>
                          ))}
                        </div>
                      ),
                    }]}
                  />
                )}
                {m.role === 'assistant' && !m.content && (
                  <Text type="secondary" style={{ fontSize: 13 }}>
                    未找到相关信息，请尝试换个问题。
                  </Text>
                )}
              </div>
            </div>
          ))}

          {streaming && (
            <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
              <Avatar icon={<RobotOutlined />} style={{ background: '#10b981', flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <Text strong style={{ fontSize: 12, color: '#94a3b8' }}>助手</Text>
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

        {/* Input */}
        <div style={{ padding: '12px 24px', borderTop: '1px solid #f0f0f0', display: 'flex', gap: 12, background: '#fff' }}>
          <TextArea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={currentConv ? '输入问题，按 Enter 发送，Shift+Enter 换行...' : '请先创建或选择一个对话'}
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={loading || !currentConv}
            style={{ flex: 1 }}
          />
          <Button
            type="primary" icon={<SendOutlined />} onClick={handleSend}
            loading={loading} size="large" disabled={!currentConv}
          >
            发送
          </Button>
        </div>
      </div>

      {/* ── Settings Drawer ── */}
      <Drawer
        title={currentConv ? '对话设置' : '新建对话'}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        size="large"
        extra={
          !currentConv && (
            <Button type="primary" onClick={handleCreate} loading={creating}>
              创建对话
            </Button>
          )
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div>
            <Text strong>知识库</Text>
            <Select
              placeholder="选择知识库"
              value={kbId}
              onChange={setKbId}
              options={kbs.map((k) => ({ value: k.kb_id, label: k.name }))}
              style={{ width: '100%', marginTop: 8 }}
              allowClear
            />
          </div>

          <div>
            <Text strong>Temperature: {modelParams.temperature}</Text>
            <Slider
              min={0} max={1} step={0.05} value={modelParams.temperature}
              onChange={(v) => setModelParams((p) => ({ ...p, temperature: v }))}
            />
          </div>

          <div>
            <Text strong>Top-P: {modelParams.top_p}</Text>
            <Slider
              min={0} max={1} step={0.05} value={modelParams.top_p}
              onChange={(v) => setModelParams((p) => ({ ...p, top_p: v }))}
            />
          </div>

          <div>
            <Text strong>相似度阈值: {modelParams.threshold}</Text>
            <Slider
              min={0} max={1} step={0.05} value={modelParams.threshold}
              onChange={(v) => setModelParams((p) => ({ ...p, threshold: v }))}
            />
          </div>

          <div>
            <Text strong>Top N 检索数量: {modelParams.top_n}</Text>
            <Select
              value={modelParams.top_n}
              onChange={(v) => setModelParams((p) => ({ ...p, top_n: v }))}
              options={[1, 2, 3, 4, 5, 6, 8, 10, 15, 20].map((n) => ({ value: n, label: String(n) }))}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>

          <div>
            <Text strong>系统提示词</Text>
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>
              使用 {'{{knowledge}}'} 作为知识库上下文变量的占位符
            </Text>
            <TextArea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              autoSize={{ minRows: 4, maxRows: 10 }}
              style={{ marginTop: 8, fontFamily: 'monospace', fontSize: 13 }}
            />
          </div>
        </div>
      </Drawer>
    </div>
  );
}
