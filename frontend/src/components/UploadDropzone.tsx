import { useRef, useState, type DragEvent } from 'react'

const MAX_UPLOAD_MB = 25

function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

/** Drag-and-drop (or click-to-browse) PDF picker. Rejects non-PDFs before uploading. */
export function UploadDropzone({
  onFiles,
  disabled = false,
}: {
  onFiles: (files: File[]) => void
  disabled?: boolean
}) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [rejected, setRejected] = useState<string | null>(null)

  function accept(list: FileList | null) {
    const files = Array.from(list ?? [])
    const pdfs = files.filter(isPdf)
    const tooBig = pdfs.filter((f) => f.size > MAX_UPLOAD_MB * 1024 * 1024)
    const ok = pdfs.filter((f) => !tooBig.includes(f))
    const problems = [
      ...files.filter((f) => !isPdf(f)).map((f) => `${f.name} is not a PDF`),
      ...tooBig.map((f) => `${f.name} is larger than ${MAX_UPLOAD_MB} MB`),
    ]
    setRejected(problems.length ? problems.join('; ') : null)
    if (ok.length) onFiles(ok)
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    if (!disabled) accept(event.dataTransfer.files)
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-disabled={disabled}
        data-testid="upload-dropzone"
        onClick={() => !disabled && input.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
            e.preventDefault()
            input.current?.click()
          }
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-white hover:bg-slate-50'
        } ${disabled ? 'cursor-not-allowed opacity-60' : ''}`}
      >
        <p className="text-sm font-medium text-slate-700">Drop PDF files here, or click to browse</p>
        <p className="mt-1 text-xs text-slate-500">PDF only, up to {MAX_UPLOAD_MB} MB each</p>
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          data-testid="upload-input"
          onChange={(e) => {
            accept(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
      {rejected ? <p className="mt-2 text-sm text-red-700">{rejected}</p> : null}
    </div>
  )
}
