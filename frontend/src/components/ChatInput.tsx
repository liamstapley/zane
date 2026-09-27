import { useState, type FormEvent } from "react";

interface Props {
  disabled: boolean;
  onSubmit: (message: string) => void;
}

export default function ChatInput({ disabled, onSubmit }: Props) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = value.trim();
    if (message === "" || disabled) {
      return;
    }
    onSubmit(message);
    setValue("");
  }

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <textarea
        className="composer-input"
        placeholder="Describe the task for ZANE..."
        value={value}
        rows={3}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />
      <div className="composer-actions">
        <span className="hint">Enter to send &middot; Shift + Enter for a new line</span>
        <button className="btn btn-primary" type="submit" disabled={disabled || value.trim() === ""}>
          {disabled ? "Working..." : "Send"}
        </button>
      </div>
    </form>
  );
}
