package com.ozkanilkay.musiki_frontend.data.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ArtistBrief(
    val id: Int,
    val username: String,
    val is_followed: Boolean = false,
    val followers_count: Int = 0,
)

@JsonClass(generateAdapter = true)
data class ArtistListItemDto(
    val id: Int,
    val username: String,
    val is_followed: Boolean = false,
    val followers_count: Int = 0,
    val songs_count: Int = 0,
)

@JsonClass(generateAdapter = true)
data class AlbumBrief(
    val id: Int,
    val title: String,
)

@JsonClass(generateAdapter = true)
data class SongDto(
    val id: Int,
    val title: String,
    val artist: ArtistBrief,
    val album: AlbumBrief?,
    val genre: String,
    val duration: Double?,
    val play_count: Int,
    val is_fingerprinted: Boolean,
    val cover_image: String?,
    val is_liked: Boolean = false,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class AlbumDto(
    val id: Int,
    val title: String,
    val artist: ArtistBrief,
    val cover_image: String?,
    val release_date: String?,
    val description: String,
    val song_count: Int,
    val is_liked: Boolean = false,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class AlbumDetailDto(
    val id: Int,
    val title: String,
    val artist: ArtistBrief,
    val cover_image: String?,
    val release_date: String?,
    val description: String,
    val song_count: Int,
    val is_liked: Boolean = false,
    val created_at: String,
    val songs: List<SongDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class ArtistDetailDto(
    val id: Int,
    val username: String,
    val is_followed: Boolean = false,
    val followers_count: Int = 0,
    val songs_count: Int = 0,
    val songs: List<SongDto> = emptyList(),
    val albums: List<AlbumDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class LikeResponse(
    val liked: Boolean,
)

@JsonClass(generateAdapter = true)
data class SongListResponse(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<SongDto>,
)

@JsonClass(generateAdapter = true)
data class ListenHistoryDto(
    val id: Int,
    val song: SongDto,
    val duration_ms: Int,
    val listened_at: String,
)

@JsonClass(generateAdapter = true)
data class RecordListenRequest(
    val song_id: Int,
    val duration_ms: Long,
)

@JsonClass(generateAdapter = true)
data class ListenHistoryResponse(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<ListenHistoryDto>,
)
