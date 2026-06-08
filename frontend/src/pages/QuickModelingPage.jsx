import { useState, useEffect, useCallback } from 'react';
import { Card, Button, Table, Space, Typography, message, Tag, Form, Input, InputNumber, Select, Switch, Collapse } from 'antd';
import { PlayCircleOutlined, ReloadOutlined, CodeOutlined, DatabaseOutlined, ApiOutlined, CheckCircleOutlined } from '@ant-design/icons';
import * as ontologyApi from '../api/ontology';
import * as modelingApi from '../api/modeling';

const { Title, Text, Paragraph } = Typography;
const DATASET_ID = '_ontology_default';

const CONNECTION_TYPES = [
  { label: '连接参数', value: 'parameters' },
  { label: 'DSN 连接串', value: 'dsn' },
  { label: '实例默认配置', value: 'default' },
];

export default function QuickModelingPage() {
  const [loading, setLoading] = useState(false);
  const [modeling, setModeling] = useState(false);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [dataSources, setDataSources] = useState([]);

  const [form] = Form.useForm();
  const [connType, setConnType] = useState('parameters');

  const fetchSources = useCallback(async () => {
    setLoading(true);
    try {
      const res = await ontologyApi.listDataSources(DATASET_ID);
      if (res.code === 0) setDataSources(res.data || []);
    } catch { /* data sources may not exist yet */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchSources(); }, [fetchSources]);

  const buildParams = (values) => {
    const params = { connection_type: connType, ...values };
    if (typeof params.exclude_tables === 'string') {
      params.exclude_tables = params.exclude_tables.split(',').map(s => s.trim()).filter(Boolean);
    }
    if (typeof params.include_tables === 'string') {
      params.include_tables = params.include_tables.split(',').map(s => s.trim()).filter(Boolean);
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

  const handleQuickModel = async () => {
    try {
      const values = await form.validateFields();
      setModeling(true);
      setResult(null);
      const params = buildParams(values);
      const res = await modelingApi.quickModel(DATASET_ID, params);
      if (res.code === 0) {
        setResult(res.data);
        message.success(`快速建模完成，生成 ${res.data.object_types?.length || 0} 个 Object Type`);
      } else {
        message.error(res.data?.error || '建模失败');
      }
    } catch { message.error('建模失败'); }
    setModeling(false);
  };

  const handleRegister = async () => {
    if (!result) return;
    setRegistering(true);
    try {
      const res = await modelingApi.registerOntology(DATASET_ID, {
        object_types: result.object_types || [],
        link_types: result.link_types || [],
        action_types: result.action_types || [],
      });
      if (res.code === 0) {
        message.success('本体定义已注册');
        fetchSources();
        setResult(null);
      }
    } catch { message.error('注册失败'); }
    setRegistering(false);
  };

  const connectionFields = (
    <>
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
      <Form.Item name="exclude_tables" label="排除表（逗号分隔）">
        <Input placeholder="table1,table2" />
      </Form.Item>
      <Form.Item name="include_tables" label="包含表（逗号分隔，留空=全部）">
        <Input placeholder="table1,table2" />
      </Form.Item>
    </>
  );

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><CodeOutlined style={{ marginRight: 8 }} />快速建模</Title>
          <Text type="secondary">基于数据库表结构直接生成本体定义，无需 LLM 分析</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchSources}>刷新</Button>
        </Space>
      </div>

      <Card title="数据源连接配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
          <Form.Item label="连接方式">
            <Select options={CONNECTION_TYPES} value={connType} onChange={setConnType} />
          </Form.Item>
          {connectionFields}
          <Space>
            <Button icon={<ApiOutlined />} onClick={handleTestConnection} loading={testing}>
              测试连接
            </Button>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleQuickModel} loading={modeling}>
              开始快速建模
            </Button>
          </Space>
        </Form>
      </Card>

      {result && (
        <Card title="建模结果" style={{ marginBottom: 16 }} extra={
          <Space>
            <Text>生成 Object Types: <Text strong>{result.object_types?.length || 0}</Text></Text>
            <Text>生成 Link Types: <Text strong>{result.link_types?.length || 0}</Text></Text>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleRegister} loading={registering}>注册本体</Button>
          </Space>
        }>
          {result.object_types?.length > 0 && (
            <Card size="small" title="Object Types" style={{ marginBottom: 12 }}>
              <Table
                dataSource={result.object_types}
                rowKey="type_name"
                size="small"
                pagination={false}
                columns={[
                  { title: 'Type Name', dataIndex: 'type_name', render: (v) => <Tag color="blue">{v}</Tag> },
                  { title: 'Display Name', dataIndex: 'display_name' },
                  { title: 'Properties', dataIndex: 'properties', render: (v) => v?.length || 0 },
                  { title: 'Source Table', dataIndex: ['source', 'table'], render: (v) => v ? <Text code>{v}</Text> : '-' },
                ]}
              />
            </Card>
          )}
          {result.link_types?.length > 0 && (
            <Card size="small" title="Link Types">
              <Table
                dataSource={result.link_types}
                rowKey="link_name"
                size="small"
                pagination={false}
                columns={[
                  { title: 'Link Name', dataIndex: 'link_name', render: (v) => <Tag color="purple">{v}</Tag> },
                  { title: 'Source', dataIndex: 'source_type' },
                  { title: 'Target', dataIndex: 'target_type' },
                ]}
              />
            </Card>
          )}
        </Card>
      )}

      <Card title="已注册的本体定义">
        <Table
          dataSource={dataSources}
          rowKey="table_name"
          loading={loading}
          columns={[
            { title: '表名', dataIndex: 'table_name', render: (v) => <Text code>{v}</Text> },
            { title: '对应 Object Type', dataIndex: 'object_type', render: (v) => v ? <Tag color="green">{v}</Tag> : '-' },
            { title: '状态', dataIndex: 'status', render: (v) => v || '-' },
          ]}
          locale={{ emptyText: '暂无已注册的数据源表，请先执行快速建模' }}
        />
      </Card>
    </div>
  );
}
