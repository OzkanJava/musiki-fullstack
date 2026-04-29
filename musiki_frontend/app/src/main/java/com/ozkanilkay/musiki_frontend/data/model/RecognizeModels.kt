package com.ozkanilkay.musiki_frontend.data.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class RecognizeSongResult(
    val song_id: Int,
    val title: String,
    val artist: String,
    val album: String?,
    val confidence: Int,
    val relative_confidence: Double? = null,
    val ratio: Double? = null,
    val match_quality: String? = null,
)

@JsonClass(generateAdapter = true)
data class RecognizeResponse(
    val song: RecognizeSongResult?,
    val candidate: RecognizeSongResult? = null,
    val detail: String?,
    val reason: String? = null,
    val total_hashes: Int? = null,
    val confidence: Int?,
    val relative_confidence: Double? = null,
    val ratio: Double? = null,
    val match_quality: String? = null,
)
