import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders model output as Markdown.
 *
 * The models emit headings, lists, tables and **bold** freely; rendering these
 * as plain text showed the raw syntax to the student.
 */
export default function Markdown({ children, className = "" }) {
  return (
    <div className={`markdown ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Open any link the model produces safely, in a new tab.
          a: ({ node: _node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
          table: ({ node: _node, ...props }) => (
            <div className="table-scroll">
              <table {...props} />
            </div>
          ),
        }}
      >
        {children ?? ""}
      </ReactMarkdown>
    </div>
  );
}
