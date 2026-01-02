import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  FolderOpen, File, Upload, Plus, Search, Trash2, 
  ExternalLink, ChevronRight, Home, RefreshCw, X,
  FileText, Image, Video, Music, Archive, Code,
  Loader2, CloudOff, Link2, FolderPlus, AlertCircle
} from 'lucide-react';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '@/components/DashboardLayout';
import { useSearchParams } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const ContentHubPage = () => {
  const [searchParams] = useSearchParams();
  const [driveConnected, setDriveConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [currentFolder, setCurrentFolder] = useState(null);
  const [folderPath, setFolderPath] = useState([{ id: null, name: 'My Drive' }]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    checkDriveStatus();
    
    // Check for connection status from callback
    const connected = searchParams.get('drive_connected');
    const error = searchParams.get('drive_error');
    
    if (connected === 'true') {
      toast.success('Google Drive connected successfully!');
      setDriveConnected(true);
      fetchFiles();
    }
    if (error) {
      toast.error(`Failed to connect: ${error}`);
    }
  }, [searchParams]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return { headers: { Authorization: `Bearer ${token}` } };
  };

  const checkDriveStatus = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/drive/status`, getAuthHeaders());
      setDriveConnected(response.data.connected);
      if (response.data.connected) {
        fetchFiles();
      }
    } catch (error) {
      console.error('Failed to check Drive status:', error);
    } finally {
      setLoading(false);
    }
  };

  const connectDrive = async () => {
    setConnecting(true);
    try {
      const response = await axios.get(`${API_URL}/api/drive/connect`, getAuthHeaders());
      if (response.data.authorization_url) {
        window.location.href = response.data.authorization_url;
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to initiate connection');
      setConnecting(false);
    }
  };

  const disconnectDrive = async () => {
    try {
      await axios.get(`${API_URL}/api/drive/disconnect`, getAuthHeaders());
      setDriveConnected(false);
      setFiles([]);
      toast.success('Google Drive disconnected');
    } catch (error) {
      toast.error('Failed to disconnect');
    }
  };

  const fetchFiles = useCallback(async (folderId = null) => {
    setLoading(true);
    try {
      const params = folderId ? `?folder_id=${folderId}` : '';
      const response = await axios.get(`${API_URL}/api/drive/files${params}`, getAuthHeaders());
      setFiles(response.data.files);
      setSearchResults(null);
    } catch (error) {
      toast.error('Failed to load files');
    } finally {
      setLoading(false);
    }
  }, []);

  const navigateToFolder = (folder) => {
    setCurrentFolder(folder.id);
    setFolderPath(prev => [...prev, { id: folder.id, name: folder.name }]);
    fetchFiles(folder.id);
  };

  const navigateToPathIndex = (index) => {
    const newPath = folderPath.slice(0, index + 1);
    setFolderPath(newPath);
    const folderId = newPath[newPath.length - 1].id;
    setCurrentFolder(folderId);
    fetchFiles(folderId);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API_URL}/api/drive/search?query=${encodeURIComponent(searchQuery)}`,
        getAuthHeaders()
      );
      setSearchResults(response.data.files);
    } catch (error) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    if (currentFolder) {
      formData.append('folder_id', currentFolder);
    }

    try {
      await axios.post(`${API_URL}/api/drive/upload`, formData, {
        ...getAuthHeaders(),
        headers: {
          ...getAuthHeaders().headers,
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('File uploaded successfully!');
      fetchFiles(currentFolder);
    } catch (error) {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const createFolder = async () => {
    if (!newFolderName.trim()) return;

    try {
      await axios.post(
        `${API_URL}/api/drive/folder`,
        null,
        {
          ...getAuthHeaders(),
          params: {
            name: newFolderName,
            parent_id: currentFolder
          }
        }
      );
      toast.success('Folder created!');
      setShowNewFolderModal(false);
      setNewFolderName('');
      fetchFiles(currentFolder);
    } catch (error) {
      toast.error('Failed to create folder');
    }
  };

  const deleteFile = async (fileId, fileName) => {
    if (!window.confirm(`Delete "${fileName}"?`)) return;

    try {
      await axios.delete(`${API_URL}/api/drive/files/${fileId}`, getAuthHeaders());
      toast.success('File deleted');
      fetchFiles(currentFolder);
    } catch (error) {
      toast.error('Failed to delete file');
    }
  };

  const getFileIcon = (mimeType) => {
    if (mimeType?.includes('folder')) return <FolderOpen className="w-8 h-8 text-yellow-500" />;
    if (mimeType?.includes('image')) return <Image className="w-8 h-8 text-green-500" />;
    if (mimeType?.includes('video')) return <Video className="w-8 h-8 text-purple-500" />;
    if (mimeType?.includes('audio')) return <Music className="w-8 h-8 text-pink-500" />;
    if (mimeType?.includes('zip') || mimeType?.includes('archive')) return <Archive className="w-8 h-8 text-orange-500" />;
    if (mimeType?.includes('code') || mimeType?.includes('javascript') || mimeType?.includes('json')) return <Code className="w-8 h-8 text-blue-500" />;
    if (mimeType?.includes('document') || mimeType?.includes('text') || mimeType?.includes('pdf')) return <FileText className="w-8 h-8 text-blue-600" />;
    return <File className="w-8 h-8 text-slate-400" />;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  const displayFiles = searchResults !== null ? searchResults : files;

  // Not connected view
  if (!driveConnected && !loading) {
    return (
      <DashboardLayout>
        <div data-testid="content-hub-page" className="max-w-2xl mx-auto py-16 text-center">
          <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-green-500 rounded-3xl flex items-center justify-center mx-auto mb-8 shadow-lg">
            <FolderOpen className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold mb-4">Content Hub</h1>
          <p className="text-secondary text-lg mb-8">
            Connect your Google Drive to access, organize, and share sales materials with your team.
          </p>
          
          <div className="bg-white rounded-2xl p-8 border border-border shadow-sm mb-8">
            <h2 className="text-xl font-semibold mb-4">Features</h2>
            <div className="grid grid-cols-2 gap-4 text-left">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FolderOpen className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium">Browse Files</p>
                  <p className="text-sm text-secondary">Navigate your Drive folders</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Upload className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium">Upload Files</p>
                  <p className="text-sm text-secondary">Add new documents easily</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Search className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="font-medium">Search</p>
                  <p className="text-sm text-secondary">Find files instantly</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Link2 className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="font-medium">Quick Share</p>
                  <p className="text-sm text-secondary">Open files in Drive</p>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={connectDrive}
            disabled={connecting}
            className="px-8 py-4 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-xl font-semibold text-lg shadow-lg shadow-blue-500/30 transition-all flex items-center gap-3 mx-auto disabled:opacity-50"
            data-testid="connect-drive-btn"
          >
            {connecting ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <svg className="w-6 h-6" viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
                <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
                <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47"/>
                <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/>
                <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
                <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
                <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
              </svg>
            )}
            {connecting ? 'Connecting...' : 'Connect Google Drive'}
          </button>

          <p className="text-sm text-secondary mt-4">
            We'll ask for permission to access your Drive files
          </p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div data-testid="content-hub-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-4xl font-bold text-foreground mb-2">Content Hub</h1>
            <p className="text-secondary">Your team's shared Google Drive files</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchFiles(currentFolder)}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={disconnectDrive}
              className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <CloudOff className="w-4 h-4" />
              Disconnect
            </button>
          </div>
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search files..."
              className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              data-testid="search-files-input"
            />
            {searchResults !== null && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults(null);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-100 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowNewFolderModal(true)}
            className="px-4 py-2 border border-border rounded-lg hover:bg-slate-50 flex items-center gap-2"
          >
            <FolderPlus className="w-5 h-5" />
            New Folder
          </button>
          <label className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 cursor-pointer flex items-center gap-2">
            {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Upload className="w-5 h-5" />}
            Upload
            <input
              type="file"
              onChange={handleUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
        </div>

        {/* Breadcrumb */}
        {searchResults === null && (
          <div className="flex items-center gap-2 mb-4 text-sm">
            {folderPath.map((folder, index) => (
              <React.Fragment key={folder.id || 'root'}>
                {index > 0 && <ChevronRight className="w-4 h-4 text-slate-400" />}
                <button
                  onClick={() => navigateToPathIndex(index)}
                  className={`flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-100 ${
                    index === folderPath.length - 1 ? 'font-medium text-primary' : 'text-slate-600'
                  }`}
                >
                  {index === 0 && <Home className="w-4 h-4" />}
                  {folder.name}
                </button>
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Search results indicator */}
        {searchResults !== null && (
          <div className="mb-4 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg flex items-center gap-2">
            <Search className="w-4 h-4" />
            <span>Search results for "{searchQuery}" ({searchResults.length} files)</span>
          </div>
        )}

        {/* Files Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : displayFiles.length === 0 ? (
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500">
              {searchResults !== null ? 'No files found' : 'This folder is empty'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {displayFiles.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-white rounded-xl border border-border p-4 hover:shadow-md transition-all group cursor-pointer"
                onClick={() => file.isFolder ? navigateToFolder(file) : window.open(file.webViewLink, '_blank')}
                data-testid={`file-${file.id}`}
              >
                <div className="flex flex-col items-center text-center">
                  <div className="mb-3 p-3 bg-slate-50 rounded-xl group-hover:bg-slate-100 transition-colors">
                    {file.thumbnailLink && !file.isFolder ? (
                      <img src={file.thumbnailLink} alt={file.name} className="w-12 h-12 object-cover rounded" />
                    ) : (
                      getFileIcon(file.mimeType)
                    )}
                  </div>
                  <p className="font-medium text-sm line-clamp-2 mb-1" title={file.name}>
                    {file.name}
                  </p>
                  <p className="text-xs text-slate-400">
                    {file.isFolder ? 'Folder' : formatFileSize(file.size)}
                  </p>
                </div>
                
                {/* Actions overlay */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                  {!file.isFolder && (
                    <a
                      href={file.webViewLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 bg-white rounded-lg shadow-sm hover:bg-slate-50"
                      title="Open in Drive"
                    >
                      <ExternalLink className="w-4 h-4 text-slate-600" />
                    </a>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteFile(file.id, file.name); }}
                    className="p-1.5 bg-white rounded-lg shadow-sm hover:bg-red-50"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* New Folder Modal */}
        <AnimatePresence>
          {showNewFolderModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
              onClick={(e) => e.target === e.currentTarget && setShowNewFolderModal(false)}
            >
              <motion.div
                initial={{ scale: 0.95 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.95 }}
                className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6"
              >
                <h3 className="text-xl font-bold mb-4">Create New Folder</h3>
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="Folder name"
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary mb-4"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && createFolder()}
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => setShowNewFolderModal(false)}
                    className="flex-1 py-2 border border-border rounded-lg hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={createFolder}
                    disabled={!newFolderName.trim()}
                    className="flex-1 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50"
                  >
                    Create
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  );
};

export default ContentHubPage;
