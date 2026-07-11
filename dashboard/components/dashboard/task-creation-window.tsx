"use client";

import { useRef, useState } from "react";

interface TaskCreationWindowProps {
  hasRunningTasks: boolean;
}

export function TaskCreationWindow({ hasRunningTasks }: TaskCreationWindowProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [taskText, setTaskText] = useState("");
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const statusLabel = hasRunningTasks ? "Queue ready" : "Ready";

  function handleSend() {
    if (!taskText.trim() && !selectedFileName) {
      return;
    }

    setTaskText("");
    setSelectedFileName(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <section className="fixed bottom-5 right-5 z-50 w-[min(92vw,26rem)] overflow-hidden rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,14,24,0.94),rgba(10,14,24,0.82))] shadow-[0_30px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl">
      <button
        type="button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
        className="flex w-full items-center justify-between gap-4 border-b border-white/10 px-4 py-3 text-left transition hover:bg-white/5"
      >
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-200/80">Task creation</p>
          <h3 className="mt-1 text-sm font-semibold text-white">Compose a new task</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em] text-cyan-100">
            {statusLabel}
          </span>
          <span
            className="grid h-8 w-8 place-items-center rounded-full border border-white/10 bg-white/5 text-sm text-zinc-100"
            aria-label={isOpen ? "Minimize task window" : "Maximize task window"}
            title={isOpen ? "Minimize task window" : "Maximize task window"}
          >
            {isOpen ? "—" : "▢"}
          </span>
        </div>
      </button>

      {isOpen ? (
        <div className="space-y-4 px-4 py-4">
          <div className="rounded-[22px] border border-white/10 bg-white/5 p-3 text-xs leading-6 text-zinc-300">
            Send a text task, attach a PDF, or use both together. This window stays open when the dashboard is idle.
          </div>

          <label className="block space-y-2">
            <span className="text-xs uppercase tracking-[0.24em] text-zinc-400">Task text</span>
            <textarea
              value={taskText}
              onChange={(event) => setTaskText(event.target.value)}
              rows={5}
              placeholder="Describe the task, add context, or paste instructions..."
              className="w-full resize-none rounded-[22px] border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition placeholder:text-zinc-500 focus:border-cyan-300/40"
            />
          </label>

          <div className="flex flex-col gap-3 sm:flex-row">
            <label className="flex flex-1 cursor-pointer items-center justify-center rounded-[20px] border border-dashed border-white/15 bg-black/20 px-4 py-3 text-sm text-zinc-300 transition hover:border-cyan-300/40 hover:bg-cyan-300/10">
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  setSelectedFileName(file ? file.name : null);
                }}
              />
              {selectedFileName ? selectedFileName : "Attach PDF"}
            </label>

            <button
              type="button"
              onClick={handleSend}
              className="rounded-[20px] border border-cyan-300/30 bg-cyan-300/10 px-5 py-3 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/20"
            >
              Send
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}