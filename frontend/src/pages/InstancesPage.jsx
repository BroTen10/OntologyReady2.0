import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Input, Select, Typography, message, Popconfirm, Card, Tag, Tabs, Form, Row, Col, InputNumber } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import api from '../api/client';

const { Title, Text } = Typography;
const DATASET_ID = '_ontology_default';

export default function InstancesPage() {
  const [activeTab, setActiveTab] = useState('objects');
  const [objects, setObjects] = useState([]);
  const [links, setLinks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [objectTypeFilter, setObjectTypeFilter] = useState(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const fetchObjects = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (objectTypeFilter) params.object_type = objectTypeFilter;
      const res = await api.get(`/datasets/${DATASET_ID}/ontology/objects`, { params });
      if (res.data.code === 0) setObjects(res.data.data?.items || res.data.data || []);
    } finally { setLoading(false); }
  }, [objectTypeFilter]);

  const fetchLinks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/datasets/${DATASET_ID}/ontology/links`);
      if (res.data.code === 0) setLinks(res.data.data?.items || res.data.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (activeTab === 'objects') fetchObjects();
    else fetchLinks();
  }, [activeTab, fetchObjects, fetchLinks]);

  const handleSearch = async () => {
    if (!searchText.trim()) { fetchObjects(); return; }
    setLoading(true);
    try {
      const res = await api.post(`/datasets/${DATASET_ID}/ontology/objects/search`, { query: searchText, filters: objectTypeFilter ? { object_type: objectTypeFilter } : {} });
      if (res.data.code === 0) setObjects(res.data.data?.items || res.data.data || []);
    } finally { setLoading(false); }
  };

  const openCreate = (type) => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ _type: type });
    setModalOpen(true);
  };

  const openEdit = (type, record) => {
    setEditing(record);
    form.setFieldsValue({ _type: type, ...record.properties, object_type: record.object_type, link_type: record.link_type, source_id: record.source_id, target_id: record.target_id });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    const type = values._type;
    delete values._type;
    setSaving(true);
    try {
      let res;
      if (type === 'object') {
        const payload = { object_type: values.object_type, properties: {} };
        delete values.object_type;
        payload.properties = values;
        if (editing) {
          res = await api.put(`/datasets/${DATASET_ID}/ontology/objects/${editing.id}`, payload);
        } else {
          res = await api.post(`/datasets/${DATASET_ID}/ontology/objects`, payload);
        }
      } else {
        const payload = { link_type: values.link_type, source_id: values.source_id, target_id: values.target_id, properties: {} };
        delete values.link_type; delete values.source_id; delete values.target_id;
        payload.properties = values;
        if (editing) {
          res = await api.put(`/datasets/${DATASET_ID}/ontology/links/${editing.id}`, payload);
        } else {
          res = await api.post(`/datasets/${DATASET_ID}/ontology/links`, payload);
        }
      }
      if (res.data.code === 0) {
        message.success(editing ? '已更新' : '已创建');
        setModalOpen(false);
        activeTab === 'objects' ? fetchObjects() : fetchLinks();
      }
    } finally { setSaving(false); }
  };

  const handleDelete = async (type, id) => {
    const res = await api.delete(`/datasets/${DATASET_ID}/ontology/${type}/${id}`);
    if (res.data.code === 0) { message.success('已删除'); activeTab === 'objects' ? fetchObjects() : fetchLinks(); }
  };

  const objectColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 140, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    { title: '类型', dataIndex: 'object_type', key: 'type', width: 130, render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '属性', dataIndex: 'properties', key: 'props', render: (props) => (
      props ? Object.entries(props).slice(0, 4).map(([k, v]) => <Tag key={k}>{k}: {typeof v === 'object' ? JSON.stringify(v) : String(v)}</Tag>) : null
    )},
    { title: '创建时间', dataIndex: 'created_at', key: 'created', width: 170, render: (v) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit('object', r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('objects', r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const linkColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 140, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    { title: '关系类型', dataIndex: 'link_type', key: 'type', width: 120, render: (v) => <Tag color="purple">{v}</Tag> },
    { title: '源', dataIndex: 'source_id', key: 'src', width: 140, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    { title: '目标', dataIndex: 'target_id', key: 'tgt', width: 140, render: (v) => <Text code style={{fontSize:12}}>{v}</Text> },
    {
      title: '操作', key: 'actions', width: 120,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit('link', r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete('links', r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>实例管理</h1>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
          {
            key: 'objects', label: `Object 实例 (${objects.length})`, children: (
              <div>
                <Space style={{ marginBottom: 16 }} wrap>
                  <Input.Search prefix={<SearchOutlined />} placeholder="搜索..." value={searchText} onChange={(e) => setSearchText(e.target.value)} onSearch={handleSearch} style={{ width: 300 }} />
                  <Input placeholder="Object Type 过滤" value={objectTypeFilter} onChange={(e) => setObjectTypeFilter(e.target.value)} style={{ width: 180 }} allowClear />
                  <Button icon={<ReloadOutlined />} onClick={fetchObjects}>刷新</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => openCreate('object')}>新建 Object</Button>
                </Space>
                <Table columns={objectColumns} dataSource={objects} rowKey="id" loading={loading} size="small" />
              </div>
            ),
          },
          {
            key: 'links', label: `Link 实例 (${links.length})`, children: (
              <div>
                <Space style={{ marginBottom: 16 }}>
                  <Button icon={<ReloadOutlined />} onClick={fetchLinks}>刷新</Button>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => openCreate('link')}>新建 Link</Button>
                </Space>
                <Table columns={linkColumns} dataSource={links} rowKey="id" loading={loading} size="small" />
              </div>
            ),
          },
        ]} />
      </Card>

      <Modal
        title={editing ? '编辑实例' : '新建实例'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="_type" hidden><Input /></Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev._type !== cur._type}>
            {({ getFieldValue }) => {
              const t = getFieldValue('_type');
              if (t === 'object') return (
                <Form.Item name="object_type" label="Object Type" rules={[{ required: true }]}>
                  <Input placeholder="如 person, company" />
                </Form.Item>
              );
              if (t === 'link') return (
                <>
                  <Form.Item name="link_type" label="Link Type" rules={[{ required: true }]}>
                    <Input placeholder="如 works_at, owns" />
                  </Form.Item>
                  <Row gutter={16}>
                    <Col span={12}><Form.Item name="source_id" label="Source ID" rules={[{ required: true }]}><Input /></Form.Item></Col>
                    <Col span={12}><Form.Item name="target_id" label="Target ID" rules={[{ required: true }]}><Input /></Form.Item></Col>
                  </Row>
                </>
              );
              return null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
