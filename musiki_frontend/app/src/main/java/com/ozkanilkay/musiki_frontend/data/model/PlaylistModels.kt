package com.ozkanilkay.musiki_frontend.data.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class PlaylistDto(
    val id: Int,
    val title: String,
    val description: String,
    val cover_image: String?,
    val item_count: Int,
    val created_at: String,
    val updated_at: String,
)

@JsonClass(generateAdapter = true)
data class PlaylistItemDto(
    val id: Int,
    val position: Int,
    val song: SongDto,
    val added_at: String,
)

@JsonClass(generateAdapter = true)
data class PlaylistDetailDto(
    val id: Int,
    val title: String,
    val description: String,
    val cover_image: String?,
    val item_count: Int,
    val created_at: String,
    val updated_at: String,
    val items: List<PlaylistItemDto>,
)

@JsonClass(generateAdapter = true)
data class PlaylistCreateRequest(
    val title: String,
    val description: String = "",
)

@JsonClass(generateAdapter = true)
data class PlaylistAddItemRequest(
    val song_id: Int,
)

@JsonClass(generateAdapter = true)
data class PlaylistListResponse(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<PlaylistDto>,
)
