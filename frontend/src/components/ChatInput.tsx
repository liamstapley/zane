import { forwardRef, type FormEvent } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
  mode: "task" | "clarify";
  onSubmit: (message: string) => void;
  onCancelClarify?: () => void;
}

const ChatInput = forwardRef<HTMLTextAreaElement, Props>(function ChatInput(
  { value, onChange, disabled, mode, onSubmit, onCancelClarify },
  ref
) {
  const clarifying = mode === "clarify";

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = value.trim();
    if (message === "" || disabled) {
      return;
    }
    onSubmit(message);
  }

  return (
    <form className={`composer ${clarifying ? "composer-clarify" : ""}`} onSubmit={handleSubmit}>
      {clarifying && (
        <div className="composer-mode">
          <span className="badge badge-warn">ANSWERING CLARIFICATION</span>
          <span className="hint">Your answer resumes the same task.</span>
          {onCancelClarify && (
            <button type="button" className="link-btn" onClick={onCancelClarify} disabled={disabled}>Start a new task instead</button>
          )}
        </div>
      )}
      <label className="sr-only" htmlFor="composer-input">{clarifying ? "Clarification answer" : "Task description"}</label>
      <textarea
        id="composer-input"
        ref={ref}
        className="composer-input"
        placeholder={clarifying ? "Answer ZANE's question..." : "Describe the task for ZANE..."}
        value={value}
        rows={3}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />
      <div className="composer-actions">
        <span className="hint">Enter to send &middot; Shift + Enter for a new line</span>
        <button className="btn btn-primary" type="submit" disabled={disabled || value.trim() === ""}>
          {disabled ? "Working..." : clarifying ? "Send answer" : "Send"}
        </button>
      </div>
    </form>
  );
});

export default ChatInput;
