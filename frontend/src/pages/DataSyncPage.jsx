import { useState, useEffect, useCallback } from 'react';
import {
  Button, Card, Form, Input, InputNumber, message, Select, Space, Steps,
  Table, Tag, Typography, Spin, Alert, Badge, Divider, Modal, Progress, Tabs,
  Tooltip, Popconfirm,
} from 'antd';
import {
  ApiOutlined, DatabaseOutlined, CloudSyncOutlined, SyncOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined,
  PauseCircleOutlined, EyeOutlined, PlayCircleOutlined, StopOutlined,
  ExclamationCircleOutlined, PlusOutlined,
} from '@ant-design/icons';
import { useParams } from 'react-router-dom';
import {
  testSyncConnection, runSync, listSyncTasks, getSyncTask,
  getSyncTaskLogs, cancelSyncTask, listSourceTables, getTableInfo,
} from '../api/sync';

const { Title, Text, Paragraph } = Typography;

const SOURCE_TYPES = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'hive', label: 'Hive' },
  { value: 'hbase', label: 'HBase' },
  { value: 'lindorm', label: 'Lindorm' },
];

const DEFAULT_PORTS = {
  postgresql: 5432, mysql: 3306, hive: 10000, hbase: 9090, lindorm: 3306,
};

const STATUS_COLORS = {
  pending: 'default', running: 'processing', completed: 'success',
  failed: 'error', cancelled: 'warning',
};

function MappingModal({ open, sourceType, tables, onOk, onCancel }) {
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableInfo, setTableInfo] = useState(null);
  const [mapping, setMapping] = useState({});
  const [loading, setLoading] = useState(false);

  const fetchTableInfo = async (tableName) => {
    if (!tableName) return;
    setLoading(true);
    try {
      const { data } = await getTableInfo({ source_type: sourceType, table: tableName });
      if (data.code === 0 && data.data) {
        setTableInfo(data.data);
        const colMap = {};
        (data.data.columns || []).forEach((c) => { colMap[c.name] = c.name; });
        setMapping({
          source_table: tableName,
          target_object_type: tableName.replace(/[^a-zA-Z0-9_]/g, '_'),
          id_column: data.data.primary_key || 'id',
          column_mapping: colMap,
          filter_condition: '',
        });
      }
    } catch { message.error('获取表结构失败'); }
    setLoading(false);
  };

  useEffect(() => {
    if (selectedTable) fetchTableInfo(selectedTable);
  }, [selectedTable]);

  const columns = tableInfo?.columns?.map((c) => ({
    title: '源列', dataIndex: 'name', key: 'name',
    render: (n) => <><Text>{n}</Text> <Tag>{c.data_type}</Tag> {c.is_primary && <Tag color="blue">PK</Tag>}</>,
  })) || [];

  const targetColumns = [
    ...columns,
    { title: '目标属性名', dataIndex: 'name', key: 'target',
      render: (n) => (
        <Input
          size="small" value={mapping.column_mapping?.[n] || n}
          onChange={(e) => setMapping((m) => ({
            ...m, column_mapping: { ...(m.column_mapping || {}), [n]: e.target.value },
          }))}
        />
      ),
    },
  ];

  return (
    <Modal title="配置表映射" open={open} width={700} onOk={() => onOk(mapping)} onCancel={onCancel}>
      <Form layout="vertical">
        <Form.Item label="源表">
          <Select
            showSearch value={selectedTable} onChange={setSelectedTable}
            options={(tables || []).map((t) => ({ value: t, label: t }))}
            placeholder="选择要同步的表"
          />
        </Form.Item>
        {loading && <Spin />}
        {tableInfo && (
          <>
            <Space>
              <Form.Item label="目标类型名">
                <Input
                  value={mapping.target_object_type}
                  onChange={(e) => setMapping((m) => ({ ...m, target_object_type: e.target.value }))}
                />
              </Form.Item>
              <Form.Item label="ID 列">
                <Input
                  value={mapping.id_column}
                  onChange={(e) => setMapping((m) => ({ ...m, id_column: e.target.value }))}
                />
              </Form.Item>
            </Space>
            <Form.Item label="过滤条件 (WHERE)">
              <Input
                value={mapping.filter_condition} placeholder="可选"
                onChange={(e) => setMapping((m) => ({ ...m, filter_condition: e.target.value }))}
              />
            </Form.Item>
            <Table
              size="small" dataSource={tableInfo.columns} columns={targetColumns}
              rowKey="name" pagination={false} scroll={{ y: 300 }}
              title={() => <Text strong>列映射 ({{ source_col: 'target_prop' }})</Text>}
            />
          </>
        )}
      </Form>
    </Modal>
  );
}

export default function DataSyncPage() {
  const { dataset_id } = useParams();
  const dataset = dataset_id || '_ontology_default';
  const [form] = Form.useForm();
  const [sourceType, setSourceType] = useState('postgresql');
  const [connecting, setConnecting] = useState(false);
  const [connectionResult, setConnectionResult] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [mappings, setMappings] = useState([]);
  const [mappingOpen, setMappingOpen] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [activeTask, setActiveTask] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logPage, setLogPage] = useState(1);
  const [activeTab, setActiveTab] = useState('config');

  const fetchTasks = useCallback(async () => {
    try {
      const { data } = await listSyncTasks({ dataset_id: dataset });
      if (data.code === 0) setTasks(data.data.items || []);
    } catch { /* ignore */ }
  }, [dataset]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  useEffect(() => {
    let timer;
    if (tasks.some((t) => t.status === 'running' || t.status === 'pending')) {
      timer = setInterval(fetchTasks, 3000);
    }
    return () => clearInterval(timer);
  }, [tasks, fetchTasks]);

  useEffect(() => {
    if (activeTask) {
      getSyncTask(activeTask.task_id).then(({ data }) => {
        if (data.code === 0) setActiveTask(data.data);
      });
    }
  }, [tasks]);

  const handleTestConnection = async () => {
    setConnecting(true);
    try {
      const vals = form.getFieldsValue();
      const params = {
        dataset_id: dataset,
        config: {
          source_type: sourceType, host: vals.host || 'localhost',
          port: vals.port || DEFAULT_PORTS[sourceType],
          database: vals.database || '', username: vals.username || '',
          password: vals.password || '', schema_name: vals.schema_name || 'public',
        },
        mappings: [],
      };
      const { data } = await testSyncConnection(params);
      setConnectionResult(data.data);
      if (data.code === 0 && data.data?.success) {
        message.success(`连接成功: ${data.data.table_count || 0} 张表`);
      } else {
        message.error(data.data?.error || '连接失败');
      }
    } catch { message.error('连接失败'); }
    setConnecting(false);
  };

  const handleStartSync = async () => {
    if (mappings.length === 0) { message.warning('请添加至少一个表映射'); return; }
    setSyncing(true);
    try {
      const vals = form.getFieldsValue();
      const params = {
        dataset_id: dataset,
        config: {
          source_type: sourceType, host: vals.host || 'localhost',
          port: vals.port || DEFAULT_PORTS[sourceType],
          database: vals.database || '', username: vals.username || '',
          password: vals.password || '', schema_name: vals.schema_name || 'public',
        },
        mappings,
      };
      const { data } = await runSync(params);
      if (data.code === 0) {
        message.success(`同步任务已启动: ${data.data?.task_id}`);
        setActiveTab('tasks');
        fetchTasks();
      }
    } catch { message.error('同步启动失败'); }
    setSyncing(false);
  };

  const handleCancelTask = async (taskId) => {
    try {
      await cancelSyncTask(taskId);
      message.success('任务已取消');
      fetchTasks();
    } catch { message.error('取消失败'); }
  };

  const handleViewLogs = async (task) => {
    setActiveTask(task);
    try {
      const { data } = await getSyncTaskLogs(task.task_id, { page: 1, page_size: 50 });
      if (data.code === 0) setLogs(data.data.items || []);
    } catch { /* ignore */ }
  };

  const handleAddMapping = (mapping) => {
    setMappings((prev) => [...prev, mapping]);
    setMappingOpen(false);
  };

  const handleRemoveMapping = (idx) => {
    setMappings((prev) => prev.filter((_, i) => i !== idx));
  };

  const taskColumns = [
    { title: '任务 ID', dataIndex: 'task_id', key: 'task_id', width: 180,
      render: (id) => <Text code>{id?.slice(0, 18)}...</Text>,
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s) => <Badge status={STATUS_COLORS[s] || 'default'} text={s} />,
    },
    { title: '进度', dataIndex: 'progress', key: 'progress', width: 150,
      render: (p, r) => <Progress percent={Math.round(p || 0)} size="small" status={r.status === 'failed' ? 'exception' : undefined} />,
    },
    { title: '已同步/总量', key: 'rows', width: 120,
      render: (_, r) => <Text>{r.synced_rows || 0} / {r.total_rows || 0}</Text>,
    },
    { title: '开始时间', dataIndex: 'started_at', key: 'started_at', width: 170,
      render: (t) => t ? new Date(t).toLocaleString() : '-',
    },
    { title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Tooltip title="查看日志"><Button size="small" icon={<EyeOutlined />} onClick={() => handleViewLogs(r)} /></Tooltip>
          {(r.status === 'running' || r.status === 'pending') && (
            <Popconfirm title="确定取消?" onConfirm={() => handleCancelTask(r.task_id)}>
              <Button size="small" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}><CloudSyncOutlined /> 数据同步</Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'config',
          label: <><ApiOutlined /> 同步配置</>,
          children: (
            <>
              <Card title="数据源连接" style={{ marginBottom: 16 }}>
                <Form form={form} layout="vertical" initialValues={{ schema_name: 'public' }}>
                  <Form.Item label="数据源类型">
                    <Select
                      value={sourceType} onChange={(v) => { setSourceType(v); form.setFieldValue('port', DEFAULT_PORTS[v]); }}
                      options={SOURCE_TYPES}
                      style={{ width: 200 }}
                    />
                  </Form.Item>
                  <Space wrap>
                    <Form.Item name="host" label="主机"><Input placeholder="localhost" style={{ width: 160 }} /></Form.Item>
                    <Form.Item name="port" label="端口"><InputNumber min={1} max={65535} style={{ width: 100 }} /></Form.Item>
                    <Form.Item name="database" label="数据库"><Input placeholder="mydb" style={{ width: 160 }} /></Form.Item>
                    <Form.Item name="username" label="用户名"><Input style={{ width: 140 }} /></Form.Item>
                    <Form.Item name="password" label="密码"><Input.Password style={{ width: 140 }} /></Form.Item>
                    <Form.Item name="schema_name" label="Schema"><Input style={{ width: 120 }} /></Form.Item>
                  </Space>
                  <Button icon={<ApiOutlined />} loading={connecting} onClick={handleTestConnection}>
                    测试连接
                  </Button>
                </Form>

                {connectionResult && (
                  <Alert
                    style={{ marginTop: 12 }}
                    type={connectionResult.success ? 'success' : 'error'}
                    message={connectionResult.success
                      ? `连接成功 — ${connectionResult.table_count || 0} 张表, 版本: ${connectionResult.version || ''}`
                      : connectionResult.error}
                    description={connectionResult.success && connectionResult.tables && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                        {(connectionResult.tables || []).map((t) => <Tag key={t}>{t}</Tag>)}
                      </div>
                    )}
                  />
                )}
              </Card>

              <Card
                title="表映射"
                extra={<Button icon={<PlusOutlined />} onClick={() => setMappingOpen(true)}>添加映射</Button>}
              >
                {mappings.length === 0 ? (
                  <Text type="secondary">暂未配置表映射，点击"添加映射"开始</Text>
                ) : (
                  <Table
                    dataSource={mappings} rowKey={(_, i) => i} pagination={false}
                    columns={[
                      { title: '源表', dataIndex: 'source_table', key: 'source' },
                      { title: '目标类型', dataIndex: 'target_object_type', key: 'target' },
                      { title: 'ID 列', dataIndex: 'id_column', key: 'id' },
                      { title: '过滤条件', dataIndex: 'filter_condition', render: (v) => v || '-' },
                      {
                        title: '列映射', dataIndex: 'column_mapping', key: 'cols',
                        render: (m) => Object.entries(m || {}).slice(0, 5).map(([k, v]) => (
                          <Tag key={k}>{k} → {v}</Tag>
                        )),
                      },
                      {
                        title: '操作', key: 'actions',
                        render: (_, __, i) => (
                          <Button size="small" danger onClick={() => handleRemoveMapping(i)}>删除</Button>
                        ),
                      },
                    ]}
                  />
                )}
                <Divider />
                <Button
                  type="primary" icon={<CloudSyncOutlined />} loading={syncing}
                  onClick={handleStartSync} disabled={mappings.length === 0}
                >
                  开始同步
                </Button>
              </Card>

              <MappingModal
                open={mappingOpen}
                sourceType={sourceType}
                tables={connectionResult?.tables || []}
                onOk={handleAddMapping}
                onCancel={() => setMappingOpen(false)}
              />
            </>
          ),
        },
        {
          key: 'tasks',
          label: <><SyncOutlined /> 任务列表</>,
          children: (
            <Card
              title="同步任务"
              extra={<Button icon={<ReloadOutlined />} onClick={fetchTasks}>刷新</Button>}
            >
              <Table
                dataSource={tasks} columns={taskColumns} rowKey="task_id"
                pagination={{ pageSize: 10 }} size="small"
                expandable={{
                  expandedRowRender: (r) => (
                    <div style={{ margin: 0 }}>
                      {r.errors?.length > 0 && (
                        <Alert
                          type="error" message="错误信息"
                          description={r.errors.map((e, i) => <div key={i}>{e}</div>)}
                          style={{ marginBottom: 8 }}
                        />
                      )}
                      <Text type="secondary">配置: {JSON.stringify(r.config)}</Text>
                    </div>
                  ),
                }}
              />
            </Card>
          ),
        },
        {
          key: 'logs',
          label: <><DatabaseOutlined /> 日志</>,
          children: activeTask ? (
            <Card
              title={`任务日志: ${activeTask.task_id?.slice(0, 24)}...`}
              extra={<Button onClick={() => setActiveTask(null)}>关闭</Button>}
            >
              {activeTask.errors?.length > 0 && (
                <Alert type="error" message="错误" description={activeTask.errors.join('; ')} style={{ marginBottom: 12 }} />
              )}
              <Table
                dataSource={logs} rowKey="id" size="small" pagination={{ pageSize: 20 }}
                columns={[
                  { title: '时间', dataIndex: 'timestamp', width: 170,
                    render: (t) => t ? new Date(t).toLocaleString() : '-',
                  },
                  { title: '级别', dataIndex: 'level', width: 60,
                    render: (l) => <Tag color={l === 'error' ? 'red' : l === 'warn' ? 'orange' : 'blue'}>{l}</Tag>,
                  },
                  { title: '表', dataIndex: 'table', width: 120, render: (t) => t || '-' },
                  { title: '消息', dataIndex: 'message', key: 'msg' },
                  { title: '行数', dataIndex: 'rows_affected', width: 80 },
                ]}
              />
            </Card>
          ) : (
            <Card>
              <Text type="secondary">在任务列表中点击查看日志图标以查看详细日志</Text>
            </Card>
          ),
        },
      ]} />
    </div>
  );
}
