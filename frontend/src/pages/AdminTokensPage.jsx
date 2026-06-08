import { useState, useEffect, useCallback } from 'react';
import { Button, Table, Modal, Input, Tag, message, Typography, Space, Tabs } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import * as tokensApi from '../api/tokens';

const { Text } = Typography;

export default function AdminTokensPage() {
  const [apiKeys, setApiKeys] = useState([]);
  const [patKeys, setPatKeys] = useState([]);
  const [loadingApiKeys, setLoadingApiKeys] = useState(false);
  const [loadingPatKeys, setLoadingPatKeys] = useState(false);
  const [apiKeyPage, setApiKeyPage] = useState(1);
  const [patPage, setPatPage] = useState(1);
  const [apiKeyTotal, setApiKeyTotal] = useState(0);
  const [patTotal, setPatTotal] = useState(0);

  const fetchApiKeys = useCallback(async (page = 1) => {
    setLoadingApiKeys(true);
    try {
      const { data: res } = await tokensApi.listAllApiKeys(page, 20);
      if (res.code === 0) {
        setApiKeys(res.data?.items || []);
        setApiKeyTotal(res.data?.page_info?.total || 0);
      }
    } catch {
      message.error('获取 API Key 列表失败');
    }
    setLoadingApiKeys(false);
  }, []);

  const fetchPatKeys = useCallback(async (page = 1) => {
    setLoadingPatKeys(true);
    try {
      const { data: res } = await tokensApi.listAllTokens(page, 20);
      if (res.code === 0) {
        setPatKeys(res.data?.items || []);
        setPatTotal(res.data?.page_info?.total || 0);
      }
    } catch {
      message.error('获取个人令牌列表失败');
    }
    setLoadingPatKeys(false);
  }, []);

  useEffect(() => { fetchApiKeys(); fetchPatKeys(); }, [fetchApiKeys, fetchPatKeys]);

  const handleRevokeApiKey = async (id) => {
    Modal.confirm({
      title: '确认撤销此 API Key？',
      content: '撤销后将立即失效。',
      okType: 'danger',
      okText: '确认撤销',
      cancelText: '取消',
      onOk: async () => {
        const { data: res } = await tokensApi.revokeApiKeyAdmin(id);
        if (res.code === 0) {
          message.success('已撤销');
          fetchApiKeys(apiKeyPage);
        }
      },
    });
  };

  const handleRevokePat = async (id) => {
    Modal.confirm({
      title: '确认撤销此个人令牌？',
      content: '撤销后将立即失效。',
      okType: 'danger',
      okText: '确认撤销',
      cancelText: '取消',
      onOk: async () => {
        const { data: res } = await tokensApi.revokeTokenAdmin(id);
        if (res.code === 0) {
          message.success('已撤销');
          fetchPatKeys(patPage);
        }
      },
    });
  };

  const handleRevokeUserPat = () => {
    Modal.confirm({
      title: '按用户批量撤销令牌',
      content: (
        <div>
          <Text>输入用户 ID，该用户的所有个人令牌将被立即撤销。</Text>
          <Input id="revoke-user-id" placeholder="用户 UUID" style={{ marginTop: 8 }} />
        </div>
      ),
      okType: 'danger',
      okText: '确认撤销',
      cancelText: '取消',
      onOk: async () => {
        const userId = document.getElementById('revoke-user-id')?.value;
        if (!userId) { message.warning('请输入用户 ID'); return Promise.reject(); }
        const { data: res } = await tokensApi.revokeUserTokensAdmin(userId);
        if (res.code === 0) {
          message.success(`已撤销 ${res.data?.revoked_count || 0} 个令牌`);
          fetchPatKeys(patPage);
        }
      },
    });
  };

  const apiKeyColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: 'Key 前缀', dataIndex: 'key_prefix', key: 'key_prefix',
      render: (v) => <Text code>{v}***</Text>,
    },
    {
      title: '权限范围', dataIndex: 'scopes', key: 'scopes',
      render: (scopes) => (scopes?.length ? scopes.map((s) => <Tag key={s} color="blue">{s}</Tag>) : <Tag>全部</Tag>),
    },
    {
      title: '创建者', dataIndex: 'created_by', key: 'created_by',
      render: (v) => <Text code>{v?.substring(0, 8)}...</Text>,
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
      render: (v) => <Tag color={v ? 'green' : 'red'}>{v ? '有效' : '已撤销'}</Tag>,
    },
    {
      title: '操作', key: 'actions',
      render: (_, record) => (
        <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleRevokeApiKey(record.id)}>
          撤销
        </Button>
      ),
    },
  ];

  const patColumns = [
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
      title: '用户', dataIndex: 'user_id', key: 'user_id',
      render: (v) => <Text code>{v?.substring(0, 8)}...</Text>,
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
      render: (v) => <Tag color={v ? 'green' : 'red'}>{v ? '有效' : '已撤销'}</Tag>,
    },
    {
      title: '操作', key: 'actions',
      render: (_, record) => (
        <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleRevokePat(record.id)}>
          撤销
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>令牌管理</Typography.Title>
      <Tabs
        defaultActiveKey="api-keys"
        items={[
          {
            key: 'api-keys',
            label: `API Key (${apiKeyTotal})`,
            children: (
              <Table
                dataSource={apiKeys}
                columns={apiKeyColumns}
                rowKey="id"
                loading={loadingApiKeys}
                pagination={{
                  current: apiKeyPage, pageSize: 20, total: apiKeyTotal,
                  onChange: (p) => { setApiKeyPage(p); fetchApiKeys(p); },
                }}
                locale={{ emptyText: '暂无 API Key' }}
              />
            ),
          },
          {
            key: 'personal-tokens',
            label: `个人令牌 (${patTotal})`,
            children: (
              <>
                <div style={{ marginBottom: 16 }}>
                  <Button danger onClick={handleRevokeUserPat}>按用户批量撤销令牌</Button>
                </div>
                <Table
                  dataSource={patKeys}
                  columns={patColumns}
                  rowKey="id"
                  loading={loadingPatKeys}
                  pagination={{
                    current: patPage, pageSize: 20, total: patTotal,
                    onChange: (p) => { setPatPage(p); fetchPatKeys(p); },
                  }}
                  locale={{ emptyText: '暂无个人令牌' }}
                />
              </>
            ),
          },
        ]}
      />
    </div>
  );
}
