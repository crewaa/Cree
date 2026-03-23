interface ProfileData {
    full_name?: string
    username: string
    profile_picture: string
    bio?: string
    is_verified?: boolean
    scraped_at?: string
    followers?: number
    following?: number
    posts_count?: number
    subscribers?: number
    total_views?: number
    total_videos?: number
}

function ProfileHeader({ profile }: { profile: ProfileData }) {
    return (
      <div className="flex items-center gap-6 rounded-xl border p-6">
        <img
          src={profile.profile_picture}
          alt={profile.username}
          className="h-24 w-24 rounded-full object-cover"
        />
  
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold">{profile.full_name || profile.username}</h2>
            {profile.is_verified && (
              <span className="text-blue-500">✔</span>
            )}
          </div>
  
          <p className="text-muted-foreground">@{profile.username}</p>
          <p className="mt-2 text-sm">{profile.bio || "No bio provided"}</p>
  
          {profile.scraped_at && (
            <p className="mt-2 text-xs text-muted-foreground">
              Last synced: {new Date(profile.scraped_at).toLocaleString()}
            </p>
          )}
        </div>
      </div>
    )
  }

  export default ProfileHeader;
