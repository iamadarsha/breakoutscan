"use client";

// Last-resort boundary: renders when the root layout itself fails, so it must bring its own <html>.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          fontFamily: "system-ui, sans-serif",
          background: "#f2f4f7",
          color: "#0e1320",
          textAlign: "center",
          padding: 24,
        }}
      >
        <h1 style={{ fontSize: 22, margin: 0 }}>BreakoutScan hit a snag.</h1>
        <p style={{ margin: 0, color: "#4a5266" }}>Reload to continue.</p>
        <button
          onClick={reset}
          style={{
            height: 36,
            padding: "0 16px",
            borderRadius: 8,
            border: 0,
            background: "#5a3fe0",
            color: "#fff",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Reload
        </button>
      </body>
    </html>
  );
}
