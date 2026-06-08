import { useState, useEffect, useCallback } from 'react';
import {
  Table, Button, Tag, Space, Modal, Typography, message, Popconfirm,
  Card, List, Spin, Empty, Upload, Input,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, UploadOutlined, FileTextOutlined,
  BookOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { listKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase, getKBStats, listDocuments, uploadDocument, deleteDocument } from '../api/rag';

const { Title, Text } = Typography;

export default function KnowledgeBasePage() {
  const [kbs, setKbs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  // Selected KB detail
  const [selectedKb, setSelectedKb] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [docs, setDocs] = useState([]);
  const [stats, setStats] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const fetchKBs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listKnowledgeBases();
      if (res.code === 0) setKbs(res.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchKBs(); }, [fetchKBs]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const res = await createKnowledgeBase(newName.trim(), newDesc.trim());
      if (res.code === 0) {
        message.success('知识库已创建');
        setCreateOpen(false);
        setNewName('');
        setNewDesc('');
        fetchKBs();
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (kbId) => {
    try {
      const res = await deleteKnowledgeBase(kbId);
      if (res.code === 0) {
        message.success('已删除');
        fetchKBs();
      }
    } catch { message.error('删除失败'); }
  };

  const handleViewDetail = async (kb) => {
    setSelectedKb(kb);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const [statsRes, docsRes] = await Promise.all([
        getKBStats(kb.kb_id),
        listDocuments(kb.kb_id),
      ]);
      if (statsRes.code === 0) setStats(statsRes.data);
      if (docsRes.code === 0) setDocs(docsRes.data || []);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleUpload = async (kbId, file) => {
    setUploading(true);
    try {
      const res = await uploadDocument(kbId, file);
      if (res.code === 0) {
        message.success(`"${file.name}" 上传成功，状态: ${res.data?.status}`);
        handleViewDetail(selectedKb);
      }
    } catch {
      message.error('上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (docId) => {
    try {
      const res = await deleteDocument(docId);
      if (res.code === 0) {
        message.success('文档已删除');
        handleViewDetail(selectedKb);
      }
    } catch { message.error('删除失败'); }
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', render: (t, r) => <Text strong>{t}</Text> },
    { title: 'ID', dataIndex: 'kb_id', key: 'kb_id', width: 140, render: (v) => <Text code>{v}</Text> },
    {
      title: '操作', key: 'actions', width: 200,
      render: (_, r) => (
        <Space>
          <Button size="small" icon={<FileTextOutlined />} onClick={() => handleViewDetail(r)}>文档</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(r.kb_id)}>
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
          <Title level={4} style={{ margin: 0 }}><BookOutlined style={{ marginRight: 8 }} />知识库管理</Title>
          <Text type="secondary">管理 RAG 知识库，上传文档并建立索引</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchKBs}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建知识库</Button>
        </Space>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={kbs}
          rowKey="kb_id"
          loading={loading}
          locale={{ emptyText: <Empty description="暂无知识库" /> }}
          pagination={false}
        />
      </Card>

      {/* Create KB Modal */}
      <Modal
        title="新建知识库"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>名称</Text>
            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="知识库名称" onPressEnter={handleCreate} />
          </div>
          <div>
            <Text strong>描述</Text>
            <Input.TextArea value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="可选描述" rows={3} />
          </div>
        </Space>
      </Modal>

      {/* KB Detail Modal */}
      <Modal
        title={`${selectedKb?.name || ''} — 文档管理`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={800}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : (
          <>
            {stats && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Space size="large">
                  <Text>文档数: <Text strong>{stats.document_count}</Text></Text>
                  <Text>Chunk 数: <Text strong>{stats.chunk_count}</Text></Text>
                </Space>
              </Card>
            )}
            <div style={{ marginBottom: 16 }}>
              <Upload
                beforeUpload={(file) => { handleUpload(selectedKb.kb_id, file); return false; }}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
              </Upload>
              <Text type="secondary" style={{ marginLeft: 8 }}>支持 PDF, Word, Markdown, TXT, HTML, CSV, Excel</Text>
            </div>
            <List
              dataSource={docs}
              renderItem={(doc) => (
                <List.Item
                  actions={[
                    <Tag color={doc.status === 'processed' ? 'green' : doc.status === 'failed' ? 'red' : doc.status === 'processing' ? 'blue' : 'default'}>{doc.status}</Tag>,
                    <Popconfirm title="确定删除？" onConfirm={() => handleDeleteDoc(doc.doc_id)}>
                      <Button size="small" danger icon={<DeleteOutlined />} />
                    </Popconfirm>,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<FileTextOutlined style={{ fontSize: 20 }} />}
                    title={doc.filename}
                    description={`ID: ${doc.doc_id}`}
                  />
                </List.Item>
              )}
              locale={{ emptyText: <Empty description="暂无文档" /> }}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
