export function extractFilenameFromDisposition(disposition?: string) {
  if (!disposition) {
    return "";
  }

  const match = disposition.match(/filename="([^"]+)"/i);
  return match?.[1] ?? "";
}

export function triggerBlobDownload(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename || "delivery-package.zip";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
