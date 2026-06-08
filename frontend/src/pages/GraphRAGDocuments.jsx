import { useEffect, useState, useCallback } from 'react';
import { Button, Card, Table, Tag, Typography, Upload, Space, message, Popconfirm, Tooltip } from 'antd';
import { UploadOutlined, DeleteOutlined, ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useSearchParams, useNavigate } from 'react-router-dom';
import * as graphragApi from '../api/graphrag';

const { Title, Text } = Typography;

const STATUS_MAP = {
  pending: { color: 'default', label: '待处理' },
  processing: { color: 'processing', label: '处理中' },
  processed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
};

export default function GraphRAGDocuments() {
  const [searchParams] = useSearchParams();
  const wsId = searchParams.get('ws') || '';
  const navigate = useNavigate();
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [workspace, setWorkspace] = useState(null);

  const loadWorkspace = useCallback(async () => {
    if (!wsId) return;
    try {
      const res = await graphragApi.getWorkspace(wsId);
      if (res.code === 0) setWorkspace(res.data);
    } catch { /* ignore */ }
  }, [wsId]);

  const loadDocs = useCallback(async () => {
    if (!wsId) return;
    setLoading(true);
    try {
      const res = await graphragApi.listDocuments(wsId);
      if (res.code === 0) setDocs(res.data || []);
    } catch { message.error('加载文档列表失败'); }
    finally { setLoading(false); }
  }, [wsId]);

  useEffect(() => { loadWorkspace(); loadDocs(); }, [loadWorkspace, loadDocs]);

  const handleUpload = async (info) => {
    const file = info.file;
    setUploading(true);
    try {
      const res = await graphragApi.uploadAndProcess(wsId, file);
      if (res.code === 0) {
        const result = res.data || {};
        message.success(`上传成功，抽取 ${result.entity_count || 0} 个实体，${result.relation_count || 0} 个关系`);
        loadDocs();
      } else {
        message.error('处理失败');
      }
    } catch { message.error('上传失败'); }
    finally { setUploading(false); }
  };

  const handleDelete = async (docId) => {
    try {
      const res = await graphragApi.deleteDocument(docId);
      if (res.code === 0) {
        message.success('已删除');
        loadDocs();
      }
    } catch { message.error('删除失败'); }
  };

  const cols = [
    { title: '文件名', dataIndex: 'filename', key: 'filename', render: (t) => <><FileTextOutlined style={{ marginRight: 8 }} />{t}</> },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80, render: (v) => <Tag>{v || '-'}</Tag> },
    { title: '大小', dataIndex: 'file_size', key: 'file_size', width: 100, render: (v) => v ? `${(v / 1024).toFixed(1)} KB` : '-' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s) => {
        const st = STATUS_MAP[s] || { color: 'default', label: s };
        return <Tag color={st.color}>{st.label}</Tag>;
      },
    },
    {
      title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (v) => v ? new Date(v).toLocaleString() : '-',
    },
    {
      title: '操作', key: 'actions', width: 80,
      render: (_, rec) => (
        <Popconfirm title="确定删除?" onConfirm={() => handleDelete(rec.doc_id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  if (!wsId) {
    return (
      <div style={{ padding: 24 }}>
        <Card><Title level={5} type="secondary">请先从知识库页面选择工作空间</Title></Card>
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>文档处理</Title>
          {workspace && <Tag color="purple">{workspace.name}</Tag>}
        </Space>
        <Space>
          <Upload customRequest={({ file, onSuccess }) => { handleUpload({ file }); onSuccess?.(); }} showUploadList={false} accept=".pdf,.docx,.doc,.md,.txt,.html,.csv,.xlsx">
            <Button type="primary" icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
          </Upload>
          <Button icon={<ReloadOutlined />} onClick={loadDocs}>刷新</Button>
        </Space>
      </div>

      <Card>
        <Table columns={cols} dataSource={docs} rowKey="doc_id" loading={loading} pagination={{ pageSize: 20 }}
          locale={{ emptyText: '暂无文档，请上传' }} size="small" />
      </Card>
    </div>
  );
}
