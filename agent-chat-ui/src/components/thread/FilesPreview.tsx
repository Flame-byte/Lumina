import React from "react";
import { cn } from "@/lib/utils";
import { File, X } from "lucide-react";

interface FilesPreviewProps {
  files: File[];
  onRemove: (idx: number) => void;
  className?: string;
}

/**
 * Display preview of files to be uploaded
 */
export const FilesPreview: React.FC<FilesPreviewProps> = ({
  files,
  onRemove,
  className,
}) => {
  if (!files.length) return null;

  return (
    <div className={cn("flex flex-wrap gap-2 p-3.5 pb-0", className)}>
      {files.map((file, idx) => (
        <div
          key={idx}
          className="flex items-center gap-2 bg-gray-100 rounded-md px-2 py-1 pr-1 text-sm"
        >
          <File className="h-4 w-4 text-gray-500" />
          <span className="max-w-[150px] truncate text-gray-700">
            {file.name}
          </span>
          <button
            onClick={() => onRemove(idx)}
            className="flex h-5 w-5 items-center justify-center rounded-full hover:bg-gray-200 text-gray-500"
            type="button"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
    </div>
  );
};
