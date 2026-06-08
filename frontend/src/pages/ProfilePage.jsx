import { useState, useEffect } from 'react';
import { Card, Descriptions, Avatar, Tag, Typography, Spin } from 'antd';
import { UserOutlined, MailOutlined, IdcardOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';

const { Title } = Typography;

export default function ProfilePage() {
  const { user } = useAuthStore();

  if (!user) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>;

  return (
    <div style={{ padding: 24, maxWidth: 700 }}>
      <Title level={4} style={{ marginBottom: 24 }}>个人中心</Title>
      <Card>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Avatar size={80} icon={<UserOutlined />} style={{ background: '#7c3aed' }} />
          <Title level={3} style={{ marginTop: 12, marginBottom: 4 }}>{user.full_name || user.username}</Title>
          <Typography.Text type="secondary">@{user.username}</Typography.Text>
        </div>
        <Descriptions bordered column={1}>
          <Descriptions.Item label={<><UserOutlined /> 用户名</>}>{user.username}</Descriptions.Item>
          <Descriptions.Item label={<><MailOutlined /> 邮箱</>}>{user.email || '-'}</Descriptions.Item>
          <Descriptions.Item label={<><IdcardOutlined /> 全名</>}>{user.full_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="用户 ID">
            <Typography.Text code style={{fontSize:12}}>{user.id || user.user_id}</Typography.Text>
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            {(user.roles || []).map((r) => <Tag key={r} color="blue">{r}</Tag>)}
            {(!user.roles || user.roles.length === 0) && '-'}
          </Descriptions.Item>
          <Descriptions.Item label="用户组">
            {(user.groups || []).map((g) => <Tag key={g} color="purple">{g}</Tag>)}
            {(!user.groups || user.groups.length === 0) && '-'}
          </Descriptions.Item>
          <Descriptions.Item label="超级管理员">{user.is_superuser ? <Tag color="red">是</Tag> : <Tag>否</Tag>}</Descriptions.Item>
          <Descriptions.Item label="状态">{user.is_active !== false ? <Tag color="green">活跃</Tag> : <Tag color="red">停用</Tag>}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{user.created_at ? new Date(user.created_at).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="最后登录">{user.last_login ? new Date(user.last_login).toLocaleString() : '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
