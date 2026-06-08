import { useState } from 'react';
import { Button, Card, Form, Input, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const { data } = await login(values.username, values.password);
      if (data.code === 0) {
        const { access_token, refresh_token, user } = data.data;
        localStorage.setItem('auth_access_token', access_token);
        localStorage.setItem('auth_refresh_token', refresh_token);
        setUser(user);
        message.success('登录成功');
        navigate('/');
      } else {
        message.error(data.message);
      }
    } catch {
      message.error('登录失败，请检查网络连接');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <Card style={styles.card} variant="outlined">
        <div style={styles.logo}>♦</div>
        <Title level={3} style={styles.title}>OntologyReady 2.0</Title>
        <Text type="secondary" style={styles.subtitle}>本体知识管理平台</Text>
        <Form onFinish={onFinish} size="large" style={styles.form}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" autoComplete="current-password" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>登 录</Button>
          </Form.Item>
        </Form>
      </Card>
      <Text type="secondary" style={styles.footer}>OntologyReady 2.0 © 2026</Text>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: 400, maxWidth: '100%',
    borderRadius: 12, textAlign: 'center', padding: '32px 24px',
    boxShadow: '0 8px 40px rgba(0,0,0,0.12)',
  },
  logo: { fontSize: 48, color: '#7c3aed', marginBottom: 8 },
  title: { marginBottom: 0, fontWeight: 700 },
  subtitle: { marginBottom: 24, display: 'block' },
  form: { textAlign: 'left', marginTop: 8 },
  footer: { marginTop: 24, color: 'rgba(255,255,255,0.7)' },
};
