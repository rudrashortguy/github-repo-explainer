import ReactMarkdown from 'react-markdown'

export default function MarkdownView({ content }) {
  return <ReactMarkdown className="prose">{content}</ReactMarkdown>
}
