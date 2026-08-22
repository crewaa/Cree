import { ResponsiveContainer } from "recharts"
import { LineChart, XAxis, YAxis, Tooltip, Line } from "recharts"


/**
 * Fields this chart reads. Callers pass richer objects (InstagramPost,
 * YouTubeVideo); TypeScript allows the extra properties because these are
 * typed values rather than object literals. There is deliberately no
 * `[key: string]` index signature — it previously forced every caller to
 * carry one, which is why these props were typed `any`.
 */
interface ChartData {
  id?: number
  likes?: number
  comments?: number
  views?: number | null
  published_at?: string
  posted_at?: string
}

function LineChartComponent({
  data,
  dataKey,
}: {
  data: ChartData[]
  dataKey: "likes" | "comments" | "views"
}) {
  // Determine the date field based on available data
  const dateKey = data[0]?.posted_at ? "posted_at" : "published_at"
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <XAxis
          dataKey={dateKey}
          tickFormatter={(v) => {
            try {
              return new Date(v).toLocaleDateString()
            } catch {
              return v
            }
          }}
        />
        <YAxis />
        <Tooltip
          // recharts types this label as ReactNode, so it is narrowed before
          // being handed to Date(). Under pnpm's resolution the looser type let
          // this through; under npm's it does not, and the npm one is right.
          labelFormatter={(v) => {
            if (typeof v !== "string" && typeof v !== "number") return v
            try {
              return new Date(v).toLocaleString()
            } catch {
              return v
            }
          }}
          formatter={(value) => [value?.toLocaleString?.() || value, dataKey]}
        />
        <Line
          type="monotone"
          dataKey={dataKey}
          strokeWidth={2}
          stroke="#3b82f6"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default LineChartComponent;
