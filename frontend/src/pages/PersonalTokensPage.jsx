import { useState, useEffect, useCallback } from 'react';
import { Button, Table, Modal, Form, Input, Select, Tag, message, Typography, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import * as tokensApi from '../api/tokens';

const { Text, Paragraph } = Typography;

export default function PersonalTokensPage() {
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newToken, setNewToken] = useState(null);
  const [form] = Form.useForm();

  const fetchTokens = useCallback(async () => {
    setLoading(true);
    try {
      const { data: res } = await tokensApi.listPersonalTokens();
      if (res.code === 0) setTokens(res.data || []);
    } catch {
      message.error('获取个人令牌列表失败');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchTokens(); }, [fetchTokens]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const { data: res } = await tokensApi.createPersonalToken(values);
      if (res.code === 0) {
        setNewToken(res.data);
        fetchTokens();
        form.resetFields();
      }
    } catch (e) {
      if (e.errorFields) return;
      message.error('创建失败');
    }
  };

  const handleRevoke = async (id) => {
    Modal.confirm({
      title: '确认撤销此个人令牌？',
      content: '撤销后使用此令牌的客户端将立即无法访问。',
      okText: '确认撤销',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        const { data: res } = await tokensApi.revokePersonalToken(id);
        if (res.code === 0) {
          message.success('已撤销');
          fetchTokens();
        }
      },
    });
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: 'Token 前缀', dataIndex: 'token_prefix', key: 'token_prefix',
      render: (v) => <Text code>{v}***</Text>,
    },
    {
      title: '权限范围', dataIndex: 'scopes', key: 'scopes',
      render: (scopes) => (scopes?.length ? scopes.map((s) => <Tag key={s} color="blue">{s}</Tag>) : <Tag>全部</Tag>),
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
      render: (v) => <Tag color={v ? 'green' : 'red'}>{v ? '有效' : '已撤销'}</Tag>,
    },
    {
      title: '过期时间', dataIndex: 'expires_at', key: 'expires_at',
      render: (v) => v ? new Date(v).toLocaleString() : <Text type="secondary">永不过期</Text>,
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (v) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: '操作', key: 'actions',
      render: (_, record) => (
        <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleRevoke(record.id)}>
          撤销
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>个人访问令牌 (PAT)</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setNewToken(null); setCreateOpen(true); }}>
          创建个人令牌
        </Button>
      </div>

      {newToken && (
        <Alert
          type="success"
          showIcon
          message="个人令牌创建成功"
          description={
            <div>
              <Text strong>请立即复制此令牌，关闭后将无法再次查看：</Text>
              <Paragraph
                copyable
                code
                style={{ marginTop: 8, padding: 8, background: '#f5f5f5', wordBreak: 'break-all' }}
              >
                {newToken.token}
              </Paragraph>
            </div>
          }
          closable
          onClose={() => setNewToken(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Table dataSource={tokens} columns={columns} rowKey="id" loading={loading} locale={{ emptyText: '暂无个人令牌' }} />

      <Modal
        title="创建个人访问令牌"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：CLI 工具" />
          </Form.Item>
          <Form.Item name="scopes" label="权限范围">
            <Select mode="tags" placeholder="输入权限范围（可选）" />
          </Form.Item>
          <Form.Item name="expires_in_days" label="有效期（天）">
            <Input type="number" placeholder="留空表示永不过期" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
