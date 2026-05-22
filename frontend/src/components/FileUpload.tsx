import { useState, useRef, useCallback } from 'react';
import { UploadCloud, FileText, X } from 'lucide-react';
import { uploadFile } from '../api/client';
import type { FileInfo } from '../types';

interface UploadingFile {
  id: string;
  filename: string;
  progress: number;
}

interface FileUploadProps {
  onUploadComplete?: () => void;
  onFileUploaded?: (fileInfo: FileInfo) => void;
}

export default function FileUpload({ onUploadComplete, onFileUploaded }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: File) => {
    const uploadId = `upload_${Date.now()}`;
    setUploadingFiles((prev) => [
      ...prev,
      { id: uploadId, filename: file.name, progress: 0 },
    ]);

    try {
      const fileInfo = await uploadFile(file, (progress) => {
        setUploadingFiles((prev) =>
          prev.map((f) =>
            f.id === uploadId ? { ...f, progress } : f
          )
        );
      }, true);  // autoReview=true — auto-trigger review on upload
      onFileUploaded?.(fileInfo);
      onUploadComplete?.();
    } catch {
      // Upload failed - show briefly then remove
    }

    // Keep progress bar at 100% briefly then remove
    setTimeout(() => {
      setUploadingFiles((prev) =>
        prev.map((f) =>
          f.id === uploadId ? { ...f, progress: 100 } : f
        )
      );
      setTimeout(() => {
        setUploadingFiles((prev) => prev.filter((f) => f.id !== uploadId));
      }, 1500);
    }, 100);
  }, [onUploadComplete, onFileUploaded]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      files.forEach(handleUpload);
    },
    [handleUpload]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      files.forEach(handleUpload);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [handleUpload]
  );

  const removeUploading = useCallback((id: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.id !== id));
  }, []);

  return (
    <div className="space-y-3">
      <div
        className={`relative border-2 rounded-lg p-10 text-center cursor-pointer transition-all duration-150 ${
          isDragOver
            ? 'border-solid border-[#533afd] bg-[rgba(83,58,253,0.04)]'
            : 'border-dashed border-[#533afd]/40 hover:border-[#533afd]/70 bg-white'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.doc"
          multiple
          onChange={handleFileSelect}
        />
        <div className="flex flex-col items-center gap-3">
          <div
            className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors duration-150 ${
              isDragOver ? 'bg-[rgba(83,58,253,0.12)]' : 'bg-[rgba(83,58,253,0.06)]'
            }`}
          >
            <UploadCloud
              className={`w-7 h-7 transition-colors duration-150 ${
                isDragOver ? 'text-[#533afd]' : 'text-[#533afd]/70'
              }`}
            />
          </div>
          <div>
            <p className="text-[15px] font-medium text-[#061b31]">
              拖拽合同文件到此处，或
              <span className="text-[#533afd] underline underline-offset-2">
                点击选择文件
              </span>
            </p>
            <p className="text-sm text-[#64748d] mt-1">
              支持 PDF、DOCX、DOC、JPG、PNG 等格式（含扫描件/图片版），单文件最大 20MB
            </p>
          </div>
        </div>
      </div>

      {/* Upload progress */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-2">
          {uploadingFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-[#e5edf5]"
            >
              <FileText className="w-5 h-5 text-[#533afd] shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#061b31] truncate">
                  {file.filename}
                </p>
                <div className="mt-1.5 w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full transition-all duration-300 ease-out"
                    style={{
                      width: `${file.progress}%`,
                      backgroundColor:
                        file.progress >= 100 ? '#15be53' : '#533afd',
                    }}
                  />
                </div>
              </div>
              <span className="text-xs text-[#64748d] shrink-0 tabular-nums">
                {file.progress}%
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeUploading(file.id);
                }}
                className="p-1 text-[#64748d] hover:text-[#ef4444] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
