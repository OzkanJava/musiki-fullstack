package com.ozkanilkay.musiki_frontend.data.remote

import com.ozkanilkay.musiki_frontend.data.model.*
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.*

interface ApiService {

    // ── Auth ────────────────────────────────────────────────────────────────

    @POST("api/auth/register/")
    suspend fun register(@Body request: RegisterRequest): Response<RegisterResponse>

    @POST("api/auth/token/")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @POST("api/auth/token/refresh/")
    suspend fun refreshToken(@Body request: RefreshRequest): Response<RefreshResponse>

    @GET("api/auth/me/")
    suspend fun getMe(): Response<UserResponse>

    @POST("api/auth/request-artist/")
    suspend fun requestArtist(@Body request: RequestArtistRequest): Response<Unit>

    // ── Music ────────────────────────────────────────────────────────────────

    @GET("api/music/songs/")
    suspend fun getSongs(
        @Query("search") search: String? = null,
        @Query("ordering") ordering: String? = null,
        @Query("page") page: Int? = null,
    ): Response<SongListResponse>

    @GET("api/music/songs/mine/")
    suspend fun getMySongs(): Response<List<SongDto>>

    @Multipart
    @POST("api/music/songs/")
    suspend fun uploadSong(
        @Part("title") title: RequestBody,
        @Part("genre") genre: RequestBody,
        @Part audio_file: MultipartBody.Part,
        @Part cover_image: MultipartBody.Part? = null,
    ): Response<SongDto>

    @GET("api/music/history/")
    suspend fun getHistory(): Response<ListenHistoryResponse>

    @POST("api/music/history/record/")
    suspend fun recordListen(@Body request: RecordListenRequest): Response<Unit>

    @Multipart
    @POST("api/music/recognize/")
    suspend fun recognizeSong(@Part audio: MultipartBody.Part): Response<RecognizeResponse>

    // ── Song likes ──────────────────────────────────────────────────────────

    @POST("api/music/songs/{id}/like/")
    suspend fun likeSong(@Path("id") songId: Int): Response<LikeResponse>

    @DELETE("api/music/songs/{id}/like/")
    suspend fun unlikeSong(@Path("id") songId: Int): Response<Unit>

    @GET("api/music/songs/liked/")
    suspend fun getLikedSongs(): Response<List<SongDto>>

    @GET("api/music/albums/{id}/")
    suspend fun getAlbumDetail(@Path("id") albumId: Int): Response<AlbumDetailDto>

    @GET("api/music/artists/{id}/")
    suspend fun getArtistDetail(@Path("id") artistId: Int): Response<ArtistDetailDto>

    @GET("api/music/artists/")
    suspend fun getArtists(
        @Query("search") search: String? = null,
    ): Response<List<ArtistListItemDto>>

    // ── Playlists ───────────────────────────────────────────────────────────

    @GET("api/music/playlists/")
    suspend fun getPlaylists(): Response<PlaylistListResponse>

    @POST("api/music/playlists/")
    suspend fun createPlaylist(@Body request: PlaylistCreateRequest): Response<PlaylistDto>

    @GET("api/music/playlists/{id}/")
    suspend fun getPlaylistDetail(@Path("id") playlistId: Int): Response<PlaylistDetailDto>

    @DELETE("api/music/playlists/{id}/")
    suspend fun deletePlaylist(@Path("id") playlistId: Int): Response<Unit>

    @POST("api/music/playlists/{id}/items/")
    suspend fun addPlaylistItem(
        @Path("id") playlistId: Int,
        @Body request: PlaylistAddItemRequest,
    ): Response<PlaylistItemDto>

    @DELETE("api/music/playlists/{id}/items/{item_id}/")
    suspend fun removePlaylistItem(
        @Path("id") playlistId: Int,
        @Path("item_id") itemId: Int,
    ): Response<Unit>

    // ── Home feed shelves ───────────────────────────────────────────────────

    @GET("api/music/home/recently-played/")
    suspend fun getRecentlyPlayed(): Response<List<SongDto>>

    @GET("api/music/home/for-you/")
    suspend fun getForYou(): Response<List<SongDto>>
}
