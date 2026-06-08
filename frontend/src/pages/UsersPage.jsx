import { useState, useEffect, useCallback } from 'react';
import { Table, Button, Space, Modal, Input, Select, Switch, Typography, message, Popconfirm, Card, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, UserOutlined } from '@ant-design/icons';
import * as adminApi from '../api/admin';

const { Title, Text } = Typography;

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '', is_active: true, is_superuser: false, roles: [], groups: [] });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.listUsers();
      if (res.code === 0) setUsers(res.data?.items || res.data || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  const openModal = (user) => {
    if (user) {
      setEditing(user);
      setForm({ username: user.username, email: user.email || '', full_name: user.full_name || '', is_active: user.is_active, is_superuser: user.is_superuser, roles: user.roles || [], groups: user.groups || [], password: '' });
    } else {
      setEditing(null);
      setForm({ username: '', email: '', full_name: '', password: '', is_active: true, is_superuser: false, roles: [], groups: [] });
    }
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      let res;
      const payload = { ...form };
      if (!editing && !payload.password) { message.error('请输入密码'); setSaving(false); return; }
      if (!payload.password) delete payload.password;
      if (editing) {
        res = await adminApi.updateUser(editing.id, payload);
      } else {
        res = await adminApi.createUser(payload);
      }
      if (res.code === 0) {
        message.success(editing ? '用户已更新' : '用户已创建');
        setModalOpen(false);
        fetchUsers();
      }
    } finally { setSaving(false); }
  };

  const handleDelete = async (id) => {
    const res = await adminApi.deleteUser(id);
    if (res.code === 0) { message.success('已删除'); fetchUsers(); }
  };

  const columns = [
    { title: '用户名', dataIndex: 'username', render: (v) => <Text strong>{v}</Text> },
    { title: '邮箱', dataIndex: 'email', render: (v) => v || '-' },
    { title: '全名', dataIndex: 'full_name', render: (v) => v || '-' },
    { title: '角色', dataIndex: 'roles', width: 200, render: (v) => (v || []).map((r) => <Tag key={r}>{r}</Tag>) },
    { title: '状态', dataIndex: 'is_active', width: 70, render: (v) => v !== false ? <Tag color="green">活跃</Tag> : <Tag color="red">停用</Tag> },
    { title: '最后登录', dataIndex: 'last_login', width: 170, render: (v) => v ? new Date(v).toLocaleString() : '-' },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openModal(r)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}><UserOutlined style={{ marginRight: 8 }} />用户管理</Title>
          <Text type="secondary">管理系统用户、角色和权限</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchUsers}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openModal(null)}>新建用户</Button>
        </Space>
      </div>

      <Card>
        <Table columns={columns} dataSource={users} rowKey="id" loading={loading} size="small" />
      </Card>

      <Modal
        title={editing ? '编辑用户' : '新建用户'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={560}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div><Text strong>用户名</Text>
            <Input value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} placeholder="登录用户名" />
          </div>
          <div><Text strong>邮箱</Text>
            <Input value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} placeholder="email@example.com" />
          </div>
          <div><Text strong>全名</Text>
            <Input value={form.full_name} onChange={(e) => setForm({...form, full_name: e.target.value})} placeholder="用户全名" />
          </div>
          <div><Text strong>{editing ? '新密码 (留空不修改)' : '密码'}</Text>
            <Input.Password value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} placeholder={editing ? '留空则不修改密码' : '设置密码'} />
          </div>
          <Space>
            <div>活跃: <Switch checked={form.is_active} onChange={(v) => setForm({...form, is_active: v})} /></div>
            <div>超级管理员: <Switch checked={form.is_superuser} onChange={(v) => setForm({...form, is_superuser: v})} /></div>
          </Space>
          <div>
            <Text strong>角色</Text>
            <Select mode="tags" value={form.roles} onChange={(v) => setForm({...form, roles: v})} style={{ width: '100%' }} placeholder="admin, developer, viewer" />
          </div>
          <div>
            <Text strong>用户组</Text>
            <Select mode="tags" value={form.groups} onChange={(v) => setForm({...form, groups: v})} style={{ width: '100%' }} placeholder="admins, developers, viewers" />
          </div>
        </Space>
      </Modal>
    </div>
  );
}
