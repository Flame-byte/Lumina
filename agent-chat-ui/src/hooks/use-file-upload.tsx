import { useState, useRef, useEffect, ChangeEvent } from "react";
import { toast } from "sonner";

// All supported file types
export const SUPPORTED_FILE_TYPES = [
  // Text types
  "text/plain",
  "text/markdown",
  "text/html",
  "text/xml",
  "application/json",
  "application/javascript",
  "text/javascript",
  "application/typescript",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  // Excel types
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
  // Audio types
  "audio/mpeg",
  "audio/wav",
  "audio/x-m4a",
  "audio/flac",
  "audio/aac",
  "audio/ogg",
  "audio/x-wma",
  // Image types
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "image/bmp",
  "image/tiff",
  // PDF
  "application/pdf",
];

interface UseFileUploadOptions {
  initialFiles?: File[];
}

/**
 * File Upload Hook
 *
 * All files are processed through the backend preprocessing API, frontend only stores file references
 */
export function useFileUpload({
  initialFiles = [],
}: UseFileUploadOptions = {}) {
  // Store files to be uploaded
  const [pendingFiles, setPendingFiles] = useState<File[]>(initialFiles);
  const dropRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const dragCounter = useRef(0);

  const isDuplicate = (file: File, files: File[]) => {
    return files.some(
      (f) => f.name === file.name && f.size === file.size
    );
  };

  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const fileArray = Array.from(files);

    const validFiles = fileArray.filter((file) =>
      SUPPORTED_FILE_TYPES.includes(file.type),
    );
    const invalidFiles = fileArray.filter(
      (file) => !SUPPORTED_FILE_TYPES.includes(file.type),
    );
    const duplicateFiles = validFiles.filter((file) =>
      isDuplicate(file, pendingFiles),
    );
    const uniqueFiles = validFiles.filter(
      (file) => !isDuplicate(file, pendingFiles),
    );

    if (invalidFiles.length > 0) {
      toast.error(
        "Invalid file type detected. Supported types: text (.txt, .md, .html, .py, .js, .ts, .json, .xml, .doc, .docx), image (.jpg, .png, .gif, .bmp, .tiff, .webp), PDF, Excel (.xlsx, .xls, .csv), Audio (.mp3, .wav, .m4a, .flac, .aac, .ogg, .wma)",
      );
    }
    if (duplicateFiles.length > 0) {
      toast.error(
        `Duplicate file(s) detected: ${duplicateFiles.map((f) => f.name).join(", ")}. Each file can only be uploaded once per message.`,
      );
    }

    // Add files to pending list
    if (uniqueFiles.length > 0) {
      setPendingFiles((prev) => [...prev, ...uniqueFiles]);
      toast.info(
        `${uniqueFiles.length} file(s) added: ${uniqueFiles.map((f) => f.name).join(", ")}`,
      );
    }

    e.target.value = "";
  };

  // Drag and drop handlers
  useEffect(() => {
    if (!dropRef.current) return;

    // Global drag events with counter for robust dragOver state
    const handleWindowDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current += 1;
        setDragOver(true);
      }
    };
    const handleWindowDragLeave = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes("Files")) {
        dragCounter.current -= 1;
        if (dragCounter.current <= 0) {
          setDragOver(false);
          dragCounter.current = 0;
        }
      }
    };
    const handleWindowDrop = async (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounter.current = 0;
      setDragOver(false);

      if (!e.dataTransfer) return;

      const files = Array.from(e.dataTransfer.files);
      const validFiles = files.filter((file) =>
        SUPPORTED_FILE_TYPES.includes(file.type),
      );
      const invalidFiles = files.filter(
        (file) => !SUPPORTED_FILE_TYPES.includes(file.type),
      );
      const duplicateFiles = validFiles.filter((file) =>
        isDuplicate(file, pendingFiles),
      );
      const uniqueFiles = validFiles.filter(
        (file) => !isDuplicate(file, pendingFiles),
      );

      if (invalidFiles.length > 0) {
        toast.error(
          "Invalid file type detected. Supported types: text (.txt, .md, .html, .py, .js, .ts, .json, .xml, .doc, .docx), image (.jpg, .png, .gif, .bmp, .tiff, .webp), PDF, Excel (.xlsx, .xls, .csv), Audio (.mp3, .wav, .m4a, .flac, .aac, .ogg, .wma)",
        );
      }
      if (duplicateFiles.length > 0) {
        toast.error(
          `Duplicate file(s) detected: ${duplicateFiles.map((f) => f.name).join(", ")}. Each file can only be uploaded once per message.`,
        );
      }

      // Add files to pending list
      if (uniqueFiles.length > 0) {
        setPendingFiles((prev) => [...prev, ...uniqueFiles]);
        toast.info(
          `${uniqueFiles.length} file(s) added: ${uniqueFiles.map((f) => f.name).join(", ")}`,
        );
      }
    };
    const handleWindowDragEnd = (e: DragEvent) => {
      dragCounter.current = 0;
      setDragOver(false);
    };
    window.addEventListener("dragenter", handleWindowDragEnter);
    window.addEventListener("dragleave", handleWindowDragLeave);
    window.addEventListener("drop", handleWindowDrop);
    window.addEventListener("dragend", handleWindowDragEnd);

    // Prevent default browser behavior for dragover globally
    const handleWindowDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("dragover", handleWindowDragOver);

    // Remove element-specific drop event (handled globally)
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(true);
    };
    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragOver(false);
    };
    const element = dropRef.current;
    element.addEventListener("dragover", handleDragOver);
    element.addEventListener("dragenter", handleDragEnter);
    element.addEventListener("dragleave", handleDragLeave);

    return () => {
      element.removeEventListener("dragover", handleDragOver);
      element.removeEventListener("dragenter", handleDragEnter);
      element.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("dragenter", handleWindowDragEnter);
      window.removeEventListener("dragleave", handleWindowDragLeave);
      window.removeEventListener("drop", handleWindowDrop);
      window.removeEventListener("dragend", handleWindowDragEnd);
      window.removeEventListener("dragover", handleWindowDragOver);
      dragCounter.current = 0;
    };
  }, [pendingFiles]);

  const removeFile = (idx: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const resetFiles = () => {
    setPendingFiles([]);
  };

  /**
   * Handle paste event for files
   */
  const handlePaste = async (
    e: React.ClipboardEvent<HTMLTextAreaElement | HTMLInputElement>,
  ) => {
    const items = e.clipboardData.items;
    if (!items) return;
    const files: File[] = [];
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) files.push(file);
      }
    }
    if (files.length === 0) {
      return;
    }
    e.preventDefault();
    const validFiles = files.filter((file) =>
      SUPPORTED_FILE_TYPES.includes(file.type),
    );
    const invalidFiles = files.filter(
      (file) => !SUPPORTED_FILE_TYPES.includes(file.type),
    );
    const duplicateFiles = validFiles.filter((file) =>
      isDuplicate(file, pendingFiles),
    );
    const uniqueFiles = validFiles.filter((file) => !isDuplicate(file, pendingFiles));
    if (invalidFiles.length > 0) {
      toast.error(
        "Invalid file type detected. Supported types: text (.txt, .md, .html, .py, .js, .ts, .json, .xml, .doc, .docx), image (.jpg, .png, .gif, .bmp, .tiff, .webp), PDF, Excel (.xlsx, .xls, .csv), Audio (.mp3, .wav, .m4a, .flac, .aac, .ogg, .wma)",
      );
    }
    if (duplicateFiles.length > 0) {
      toast.error(
        `Duplicate file(s) detected: ${duplicateFiles.map((f) => f.name).join(", ")}. Each file can only be uploaded once per message.`,
      );
    }

    // Add files to pending list
    if (uniqueFiles.length > 0) {
      setPendingFiles((prev) => [...prev, ...uniqueFiles]);
      toast.info(
        `${uniqueFiles.length} file(s) added: ${uniqueFiles.map((f) => f.name).join(", ")}`,
      );
    }
  };

  return {
    pendingFiles,
    setPendingFiles,
    handleFileUpload,
    dropRef,
    removeFile,
    resetFiles,
    dragOver,
    handlePaste,
  };
}
