import { clsx, type ClassValue } from 'clsx';
import { formatDistanceToNowStrict } from 'date-fns';

/**
 * Merge class names conditionally (clsx + Tailwind-safe)
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Format a timestamp to a relative time string.
 * e.g. "3d ago", "2h ago", "just now"
 */
export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const distance = formatDistanceToNowStrict(date, { addSuffix: true });
    // Shorten common patterns
    return distance
      .replace(' seconds', 's')
      .replace(' second', 's')
      .replace(' minutes', 'm')
      .replace(' minute', 'm')
      .replace(' hours', 'h')
      .replace(' hour', 'h')
      .replace(' days', 'd')
      .replace(' day', 'd')
      .replace(' months', 'mo')
      .replace(' month', 'mo')
      .replace(' years', 'y')
      .replace(' year', 'y');
  } catch {
    return '';
  }
}

/**
 * Format bytes to human-readable file size.
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes == null || bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

/**
 * Get a Lucide icon name based on MIME type.
 */
export function getFileTypeIcon(mimeType: string): string {
  const map: Record<string, string> = {
    'application/pdf': 'FileText',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'FileText',
    'application/msword': 'FileText',
    'text/plain': 'FileType',
    'text/markdown': 'FileCode',
    'text/csv': 'Table',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Table',
    'application/vnd.ms-excel': 'Table',
    'application/vnd.google-apps.document': 'FileText',
    'application/vnd.google-apps.spreadsheet': 'Table',
  };
  return map[mimeType] || 'File';
}

/**
 * Get a human-readable label for a MIME type.
 */
export function getMimeTypeLabel(mimeType: string): string {
  const map: Record<string, string> = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/msword': 'DOC',
    'text/plain': 'TXT',
    'text/markdown': 'MD',
    'text/csv': 'CSV',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
    'application/vnd.ms-excel': 'XLS',
    'application/vnd.google-apps.document': 'Google Doc',
    'application/vnd.google-apps.spreadsheet': 'Google Sheet',
  };
  return map[mimeType] || 'File';
}

/**
 * Get provider display name.
 */
export function getProviderLabel(provider: string): string {
  const map: Record<string, string> = {
    google_drive: 'Google Drive',
    local: 'Uploaded',
    github: 'GitHub',
    gmail: 'Gmail',
    notion: 'Notion',
    dropbox: 'Dropbox',
    slack: 'Slack',
    onedrive: 'OneDrive',
  };
  return map[provider] || provider;
}

/**
 * Truncate text with ellipsis.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 1) + '…';
}

/**
 * Decode JWT payload without verification (client-side only).
 */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    const decoded = atob(payload);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}
