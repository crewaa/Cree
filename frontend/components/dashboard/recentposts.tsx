import { Heart, MessageCircle } from "lucide-react"

interface InstagramPost {
    id: number
    shortcode: string
    likes: number
    comments: number
    views: number | null
    caption: string
    posted_at: string
    is_video: boolean
  }

function RecentPosts({ posts }: { posts: InstagramPost[] }) {
    return (
      <div className="rounded-xl border p-4">
        <h3 className="mb-4 font-semibold">Recent Posts</h3>
  
        <div className="space-y-3">
          {posts.slice(0, 6).map(post => (
            <div
              key={post.id}
              className="rounded-lg border p-3 flex justify-between gap-4"
            >
              <div className="flex-1">
                <p className="text-sm line-clamp-2">{post.caption}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {new Date(post.posted_at).toLocaleString()}
                </p>
              </div>
  
              <div className="flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1"><Heart className="h-3.5 w-3.5" /> {post.likes.toLocaleString()}</span>
                <span className="flex items-center gap-1"><MessageCircle className="h-3.5 w-3.5" /> {post.comments.toLocaleString()}</span>
                {post.is_video && post.views && (
                  <span>▶ {post.views.toLocaleString()}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  export default RecentPosts;
  