package com.ozkanilkay.musiki_frontend.data.model

import android.net.Uri

data class LocalTrack(
    val id: Long,
    val title: String,
    val artist: String,
    val album: String?,
    val durationMs: Long,
    val contentUri: Uri,
    val albumArtUri: Uri?,
)

fun LocalTrack.toSongDto(): SongDto = SongDto(
    id = id.toInt(),
    title = title,
    artist = ArtistBrief(id = 0, username = artist),
    album = album?.let { AlbumBrief(id = 0, title = it) },
    genre = "Local",
    duration = durationMs / 1000.0,
    play_count = 0,
    is_fingerprinted = false,
    cover_image = albumArtUri?.toString(),
    is_liked = false,
    created_at = "",
)
