import { useState, useEffect, useRef, useCallback } from 'react';
import type { WebviewMessage } from '../types';
import type { FormatDocResult } from '../context/DashboardContext';

export type DocEditorPhase = 'idle' | 'drafting' | 'formatting' | 'reviewing' | 'saving' | 'error';

interface UseDocEditorOptions {
  tier: 'vision' | 'architecture';
  defaultName: string;
  sendMessage: (msg: WebviewMessage) => void;
  lastFormatResult: FormatDocResult | null;
  docCount: number;
}

export interface UseDocEditorReturn {
  docName: string;
  setDocName: (name: string) => void;
  isNameLocked: boolean;
  toggleNameLock: () => void;
  content: string;
  setContent: (content: string) => void;
  phase: DocEditorPhase;
  errorMessage: string | null;
  errorContext: 'format' | 'save' | null;
  handleFormat: () => void;
  handleSave: () => void;
  handleReformat: () => void;
  handleSaveAsIs: () => void;
  handleReset: () => void;
}

export function useDocEditor({
  tier,
  defaultName,
  sendMessage,
  lastFormatResult,
  docCount,
}: UseDocEditorOptions): UseDocEditorReturn {
  const [docName, setDocName] = useState(defaultName);
  const [isNameLocked, setIsNameLocked] = useState(true);
  const [content, setContent] = useState('');
  const [phase, setPhase] = useState<DocEditorPhase>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorContext, setErrorContext] = useState<'format' | 'save' | null>(null);
  const pendingRequestId = useRef<string | null>(null);
  const docCountAtSave = useRef<number>(docCount);

  // Auto-transition from idle to drafting when content changes
  const handleSetContent = useCallback(
    (value: string) => {
      setContent(value);
      if (phase === 'idle' && value.length > 0) {
        setPhase('drafting');
      } else if (phase === 'drafting' && value.length === 0) {
        setPhase('idle');
      }
    },
    [phase],
  );

  // Handle format result from backend
  useEffect(() => {
    if (!lastFormatResult || phase !== 'formatting') return;
    if (lastFormatResult.requestId !== pendingRequestId.current) return;

    pendingRequestId.current = null;

    if (lastFormatResult.success && lastFormatResult.formattedContent) {
      setContent(lastFormatResult.formattedContent);
      setPhase('reviewing');
      setErrorMessage(null);
      setErrorContext(null);
    } else {
      setPhase('error');
      setErrorContext('format');
      setErrorMessage(lastFormatResult.error || 'Formatting failed');
    }
  }, [lastFormatResult, phase]);

  // Detect document creation success (docCount increased after save)
  useEffect(() => {
    if (phase === 'saving' && docCount > docCountAtSave.current) {
      // Document was created — reset
      setDocName(defaultName);
      setIsNameLocked(true);
      setContent('');
      setPhase('idle');
      setErrorMessage(null);
      setErrorContext(null);
    }
  }, [docCount, phase, defaultName]);

  const handleFormat = useCallback(() => {
    if (!content.trim()) return;
    const requestId = `fmt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    pendingRequestId.current = requestId;
    setPhase('formatting');
    setErrorMessage(null);
    setErrorContext(null);
    sendMessage({
      type: 'formatDocContent',
      tier,
      rawContent: content,
      requestId,
    });
  }, [content, tier, sendMessage]);

  const handleSave = useCallback(() => {
    if (!docName.trim() || !content.trim()) return;
    docCountAtSave.current = docCount;
    setPhase('saving');
    setErrorMessage(null);
    setErrorContext(null);
    sendMessage({
      type: tier === 'vision' ? 'createVisionDoc' : 'createArchDoc',
      name: docName.trim(),
      content,
    });
  }, [docName, content, tier, sendMessage, docCount]);

  const handleReformat = useCallback(() => {
    handleFormat();
  }, [handleFormat]);

  const handleSaveAsIs = useCallback(() => {
    handleSave();
  }, [handleSave]);

  const handleReset = useCallback(() => {
    setDocName(defaultName);
    setIsNameLocked(true);
    setContent('');
    setPhase('idle');
    setErrorMessage(null);
    setErrorContext(null);
    pendingRequestId.current = null;
  }, [defaultName]);

  const toggleNameLock = useCallback(() => {
    if (isNameLocked) {
      setIsNameLocked(false);
    } else {
      setDocName(defaultName);
      setIsNameLocked(true);
    }
  }, [isNameLocked, defaultName]);

  return {
    docName,
    setDocName,
    isNameLocked,
    toggleNameLock,
    content,
    setContent: handleSetContent,
    phase,
    errorMessage,
    errorContext,
    handleFormat,
    handleSave,
    handleReformat,
    handleSaveAsIs,
    handleReset,
  };
}
