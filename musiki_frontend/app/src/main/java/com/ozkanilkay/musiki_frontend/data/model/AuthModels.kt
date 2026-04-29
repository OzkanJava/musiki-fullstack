package com.ozkanilkay.musiki_frontend.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(
    val username: String,
    val password: String,
)

@JsonClass(generateAdapter = true)
data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String,
    @Json(name = "password_confirm") val passwordConfirm: String,
)

@JsonClass(generateAdapter = true)
data class TokenResponse(
    val access: String,
    val refresh: String,
)

@JsonClass(generateAdapter = true)
data class RefreshRequest(
    val refresh: String,
)

@JsonClass(generateAdapter = true)
data class RefreshResponse(
    val access: String,
)

@JsonClass(generateAdapter = true)
data class RegisterResponse(
    val id: Int,
    val username: String,
    val email: String,
)

@JsonClass(generateAdapter = true)
data class UserResponse(
    val id: Int,
    val username: String,
    val email: String,
    val role: String,
    val bio: String,
    @Json(name = "is_approved_artist") val isApprovedArtist: Boolean,
    @Json(name = "date_joined") val dateJoined: String,
)

@JsonClass(generateAdapter = true)
data class RequestArtistRequest(
    val bio: String,
)
