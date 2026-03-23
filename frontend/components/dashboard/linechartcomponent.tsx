import { ResponsiveContainer } from "recharts"
import { LineChart, XAxis, YAxis, Tooltip, Line } from "recharts"


interface ChartData {
  id?: number
  likes?: number
  comments?: number
  views?: number | null
  published_at?: string
  posted_at?: string
  [key: string]: any
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
          labelFormatter={(v) => {
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
