import { useState } from 'react';
import { Card, Button, Table, Space, Typography, message, Tag, Alert, Form, Input, InputNumber, Select, Collapse } from 'antd';
import { ReloadOutlined, CheckCircleOutlined, SyncOutlined, ExclamationCircleOutlined, ApiOutlined } from '@ant-design/icons';
import * as modelingApi from '../api/modeling';

const { Title, Text } = Typography;
const DATASET_ID = '_ontology_default';

const CONNECTION_TYPES = [
  { label: '连接参数', value: 'parameters' },
  { label: 'DSN 连接串', value: 'dsn' },
  { label: '实例默认配置', value: 'default' },
];

export default function StructureChangesPage() {
  const [form] = Form.useForm();
  const [connType, setConnType] = useState('parameters');
  const [diff, setDiff] = useState(null);
  const [checking, setChecking] = useState(false);
  const [testing, setTesting] = useState(false);
  const [applying, setApplying] = useState(false);

  const buildParams = (values) => {
    const params = { connection_type: connType, ...values };
    if (typeof params.exclude_tables === 'string') {
      params.exclude_tables = params.exclude_tables.split(',').map(s => s.trim()).filter(Boolean);
    } else if (!params.exclude_tables) {
      params.exclude_tables = [];
    }
    if (typeof params.include_tables === 'string') {
      params.include_tables = params.include_tables.split(',').map(s => s.trim()).filter(Boolean);
    } else if (!params.include_tables) {
      params.include_tables = [];
    }
    return params;
  };

  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields();
      setTesting(true);
      const params = buildParams(values);
      const res = await modelingApi.testConnection(DATASET_ID, params);
      if (res.code === 0 && res.data?.success) {
        message.success(`连接成功，发现 ${res.data.table_count} 张表`);
      } else {
        message.error(res.data?.error || '连接失败');
      }
    } catch { /* validation error */ }
    setTesting(false);
  };

  const handleCheck = async () => {
    try {
      const values = await form.validateFields();
      setChecking(true);
      setDiff(null);
      const params = buildParams(values);
      const res = await modelingApi.detectChanges(DATASET_ID, params);
      if (res.code === 0) {
        setDiff(res.data);
        if (!res.data?.changes?.length) {
          message.info('未检测到结构变更');
        }
      } else {
        message.error(res.data?.error || '检测失败');
      }
    } catch { message.error('检测失败'); }
    setChecking(false);
  };

  const handleApply = async () => {
    if (!diff) return;
    setApplying(true);
    try {
      // Re-run quick model on the same connection to get updated ontology
      const values = form.getFieldsValue();
      const params = buildParams(values);

      // Apply changes by re-generating and registering ontology
      const modelRes = await modelingApi.quickModel(DATASET_ID, params);
      if (modelRes.code === 0 && modelRes.data?.object_types) {
        const regRes = await modelingApi.registerOntology(DATASET_ID, {
          object_types: modelRes.data.object_types || [],
          link_types: modelRes.data.link_types || [],
          action_types: modelRes.data.action_types || [],
        });
        if (regRes.code === 0) {
          message.success(`变更已应用，更新了 ${modelRes.data.object_types?.length || 0} 个 Object Type`);
          setDiff(null);
        }
      }
    } catch { message.error('应用失败'); }
    setApplying(false);
  };

  const changeTypeColor = (v) => v === 'added' ? 'green' : v === 'modified' ? 'blue' : 'red';
  const entityTypeLabel = (v) => v === 'object_type' ? '对象类型' : '属性';
  const changeTypeLabel = (v) => v === 'added' ? '新增' : v === 'modified' ? '修改' : '删除';

  const changeColumns = [
    { title: '变更类型', dataIndex: 'type', key: 'type', width: 100, render: (v) => <Tag color={changeTypeColor(v)}>{changeTypeLabel(v)}</Tag> },
    { title: '实体类型', dataIndex: 'entity_type', key: 'entity', width: 100, render: (v) => <Tag>{entityTypeLabel(v)}</Tag> },
    { title: '对象', dataIndex: 'object_type', key: 'obj', render: (v) => <Text code>{v}</Text> },
    { title: '字段/属性', dataIndex: 'field', key: 'field', render: (v) => <Text strong>{v || '-'}</Text> },
    { title: '旧值', dataIndex: 'old_value', key: 'old', render: (v) => v !== undefined && v !== null ? <Text delete type="danger">{String(v)}</Text> : '-' },
    { title: '新值', dataIndex: 'new_value', key: 'new', render: (v) => v !== undefined && v !== null ? <Text type="success">{String(v)}</Text> : '-' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><SyncOutlined style={{ marginRight: 8 }} />结构变更检测</Title>
          <Text type="secondary">对比数据库 Schema 与已注册 Ontology，发现结构差异</Text>
        </div>
      </div>

      <Card title="数据源连接配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="连接方式">
            <Select options={CONNECTION_TYPES} value={connType} onChange={setConnType} />
          </Form.Item>
          {connType === 'parameters' && (
            <>
              <Form.Item name="host" label="主机" rules={[{ required: true }]} initialValue="localhost">
                <Input placeholder="localhost" />
              </Form.Item>
              <Form.Item name="port" label="端口" rules={[{ required: true }]} initialValue={5432}>
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="database" label="数据库名" rules={[{ required: true }]}>
                <Input placeholder="postgres" />
              </Form.Item>
              <Form.Item name="username" label="用户名" initialValue="postgres">
                <Input placeholder="postgres" />
              </Form.Item>
              <Form.Item name="password" label="密码">
                <Input.Password placeholder="密码" />
              </Form.Item>
            </>
          )}
          {connType === 'dsn' && (
            <Form.Item name="dsn" label="DSN 连接串" rules={[{ required: true }]}>
              <Input placeholder="postgresql://user:pass@host:port/db" />
            </Form.Item>
          )}
          {connType === 'default' && (
            <Text type="secondary">将使用数据集实例的默认连接配置</Text>
          )}
          <Form.Item name="schema_name" label="Schema" initialValue="public">
            <Input placeholder="public" />
          </Form.Item>
          <Space>
            <Button icon={<ApiOutlined />} onClick={handleTestConnection} loading={testing}>
              测试连接
            </Button>
            <Button type="primary" icon={<ExclamationCircleOutlined />} onClick={handleCheck} loading={checking}>
              检测变更
            </Button>
          </Space>
        </Form>
      </Card>

      {diff && diff.changes?.length > 0 && (
        <Card
          title={<>检测到 {diff.changes.length} 项变更（新增: {diff.summary?.added || 0}，修改: {diff.summary?.modified || 0}，删除: {diff.summary?.deleted || 0}）</>}
          style={{ marginBottom: 16 }}
          extra={<Button type="primary" icon={<CheckCircleOutlined />} onClick={handleApply} loading={applying}>应用变更</Button>}
        >
          <Table columns={changeColumns} dataSource={diff.changes} rowKey={(_, i) => i} size="small" pagination={false} />
        </Card>
      )}

      {diff && (!diff.changes || diff.changes.length === 0) && (
        <Alert type="success" message="数据库 Schema 与已注册 Ontology 定义一致，无需更新" showIcon style={{ marginBottom: 16 }} />
      )}

      {!diff && (
        <Alert type="info" message="配置数据源连接后，点击「检测变更」对比数据库 Schema 与已注册 Ontology 定义的差异" showIcon />
      )}
    </div>
  );
}
