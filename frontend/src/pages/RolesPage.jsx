import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Input, Typography, message, Popconfirm, Card, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, TeamOutlined } from '@ant-design/icons';
import * as adminApi from '../api/admin';

const { Title, Text } = Typography;

export default function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.listRoles();
      if (res.code === 0) setRoles(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const openModal = (role) => {
    if (role) { setEditing(role); setName(role.name); setDesc(role.description || ''); }
    else { setEditing(null); setName(''); setDesc(''); }
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const payload = { name: name.trim(), description: desc.trim() };
      let res;
      if (editing) { res = await adminApi.updateRole(editing.name, payload); }
      else { res = await adminApi.createRole(payload); }
      if (res.code === 0) {
        message.success(editing ? '已更新' : '已创建');
        setModalOpen(false);
        fetchAll();
      }
    } finally { setSaving(false); }
  };

  const handleDelete = async (rname) => {
    const res = await adminApi.deleteRole(rname);
    if (res.code === 0) { message.success('已删除'); fetchAll(); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', render: (v) => <Text code strong>{v}</Text> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '系统角色', dataIndex: 'is_system', width: 90, render: (v) => v ? <Tag color="purple">系统</Tag> : <Tag>自定义</Tag> },
    {
      title: '操作', key: 'actions', width: 150,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal(r)} />
          {!r.is_system && (
            <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.name)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><TeamOutlined style={{ marginRight: 8 }} />角色管理</Title>
          <Text type="secondary">admin / developer / viewer 为系统角色，不可删除</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAll}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal(null)}>新建角色</Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={roles} rowKey="name" loading={loading} pagination={false} />
      </Card>

      <Modal title={editing ? '编辑角色' : '新建角色'} open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} confirmLoading={saving}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div><Text strong>名称</Text><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="角色名" onPressEnter={handleSave} /></div>
          <div><Text strong>描述</Text><Input.TextArea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} /></div>
        </Space>
      </Modal>
    </div>
  );
}
