package com.ozkanilkay.musiki_frontend.data.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class RecognizeArtistRef(
    val id: Int,
    val username: String,
)

@JsonClass(generateAdapter = true)
data class RecognizeAlbumRef(
    val id: Int,
    val title: String,
)

@JsonClass(generateAdapter = true)
data class RecognizeSongResult(
    val song_id: Int,
    val title: String,
    val artist: RecognizeArtistRef,
    val album: RecognizeAlbumRef? = null,
    val cover_image: String? = null,
)

@JsonClass(generateAdapter = true)
data class RecognizeResponse(
    val accepted: Boolean,
    val candidates: List<RecognizeSongResult> = emptyList(),
    val reason: String? = null,
    val detail: String? = null,
)
