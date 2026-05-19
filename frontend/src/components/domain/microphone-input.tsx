"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { TranscribeResponse } from "@/types/api";

const MAX_RECORDING_DURATION_SECONDS = 60;

interface MicrophoneInputProps {
  onTranscript: (transcript: string, language?: string | null) => void;
  disabled?: boolean;
}

export function MicrophoneInput({
  onTranscript,
  disabled = false,
}: MicrophoneInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isCanceledRef = useRef(false);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current = null;
      }
    };
  }, []);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      isCanceledRef.current = false;
      
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm",
      });
      
      chunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }
        
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        
        // Only transcribe if recording was not canceled
        if (!isCanceledRef.current && chunksRef.current.length > 0) {
          const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
          await transcribeAudio(audioBlob);
        } else {
          setElapsedSeconds(0);
        }
        
        chunksRef.current = [];
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setElapsedSeconds(0);
      
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => {
          const nextSecond = prev + 1;
          
          // Auto-stop recording when max duration is reached
          if (nextSecond >= MAX_RECORDING_DURATION_SECONDS) {
            // Use setTimeout to avoid calling stopRecording inside state update
            setTimeout(() => {
              stopRecording();
              toast.info("Recording stopped", {
                description: `Maximum recording duration of ${MAX_RECORDING_DURATION_SECONDS} seconds reached.`,
              });
            }, 0);
          }
          
          return nextSecond;
        });
      }, 1000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      
      if (errorMessage.includes("Permission denied")) {
        toast.error("Microphone permission denied", {
          description: "Please allow microphone access to use speech input.",
        });
      } else if (errorMessage.includes("not found")) {
        toast.error("No microphone found", {
          description: "Please connect a microphone and try again.",
        });
      } else {
        toast.error("Could not start recording", {
          description: errorMessage,
        });
      }
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      isCanceledRef.current = false;
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }

  function cancelRecording() {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      isCanceledRef.current = true;
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clean up immediately for cancel
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      chunksRef.current = [];
      setElapsedSeconds(0);
    }
  }

  async function transcribeAudio(audioBlob: Blob) {
    setIsTranscribing(true);
    
    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");
      
      const response = await api.upload<TranscribeResponse>(
        "/speech/transcribe",
        formData,
      );
      
      if (response.transcript) {
        onTranscript(response.transcript, response.language ?? null);
        toast.success("Transcribed successfully", {
          description: `${response.transcript.slice(0, 50)}${response.transcript.length > 50 ? "..." : ""}`,
        });
      } else {
        toast.error("Transcription failed", {
          description: "No transcript returned",
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      toast.error("Transcription failed", {
        description: errorMessage,
      });
    } finally {
      setIsTranscribing(false);
      setElapsedSeconds(0);
    }
  }

  function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  if (isRecording) {
    const remainingSeconds = MAX_RECORDING_DURATION_SECONDS - elapsedSeconds;
    const isNearLimit = remainingSeconds <= 10;
    
    return (
      <div className="flex items-center gap-2">
        <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
          isNearLimit 
            ? "border-amber-200 bg-amber-50" 
            : "border-red-200 bg-red-50"
        }`}>
          <div className={`h-2 w-2 animate-pulse rounded-full ${
            isNearLimit ? "bg-amber-500" : "bg-red-500"
          }`} />
          <span className={`text-sm font-medium ${
            isNearLimit ? "text-amber-700" : "text-red-700"
          }`}>
            {formatTime(elapsedSeconds)}
          </span>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={stopRecording}
          disabled={isTranscribing}
        >
          <MicOff className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={cancelRecording}
          disabled={isTranscribing}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <Button
      type="button"
      size="sm"
      variant="outline"
      onClick={startRecording}
      disabled={disabled || isTranscribing}
      loading={isTranscribing}
      title={`Record voice input (max ${MAX_RECORDING_DURATION_SECONDS}s)`}
    >
      <Mic className="h-4 w-4" />
    </Button>
  );
}