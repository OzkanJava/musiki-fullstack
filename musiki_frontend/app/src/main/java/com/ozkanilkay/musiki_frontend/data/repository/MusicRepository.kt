package com.ozkanilkay.musiki_frontend.data.repository

import com.ozkanilkay.musiki_frontend.data.model.AlbumDetailDto
import com.ozkanilkay.musiki_frontend.data.model.ArtistDetailDto
import com.ozkanilkay.musiki_frontend.data.model.ArtistListItemDto
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MusicRepository @Inject constructor(private val api: ApiService) {

    suspend fun getSongs(ordering: String = "-created_at"): Result<List<SongDto>> = try {
        val resp = api.getSongs(ordering = ordering)
        if (resp.isSuccessful) Result.success(resp.body()!!.results)
        else Result.failure(Exception("Şarkılar alınamadı (${resp.code()})"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun searchSongs(query: String): Result<List<SongDto>> = try {
        val resp = api.getSongs(search = query)
        if (resp.isSuccessful) Result.success(resp.body()!!.results)
        else Result.failure(Exception("Arama başarısız"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ── Home shelves ────────────────────────────────────────────────────────

    suspend fun getRecentlyPlayed(): Result<List<SongDto>> = try {
        val resp = api.getRecentlyPlayed()
        if (resp.isSuccessful) Result.success(resp.body().orEmpty())
        else Result.failure(Exception("Son çalınanlar alınamadı"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getForYou(): Result<List<SongDto>> = try {
        val resp = api.getForYou()
        if (resp.isSuccessful) Result.success(resp.body().orEmpty())
        else Result.failure(Exception("Öneriler alınamadı"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ── Song likes ──────────────────────────────────────────────────────────

    suspend fun likeSong(songId: Int): Result<Unit> = try {
        val resp = api.likeSong(songId)
        if (resp.isSuccessful) Result.success(Unit)
        else Result.failure(Exception("Beğenilemedi (${resp.code()})"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun unlikeSong(songId: Int): Result<Unit> = try {
        val resp = api.unlikeSong(songId)
        if (resp.isSuccessful) Result.success(Unit)
        else Result.failure(Exception("Beğeni kaldırılamadı (${resp.code()})"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getLikedSongs(): Result<List<SongDto>> = try {
        val resp = api.getLikedSongs()
        if (resp.isSuccessful) Result.success(resp.body().orEmpty())
        else Result.failure(Exception("Beğenilenler alınamadı"))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ── Album / Artist detail ───────────────────────────────────────────────

    suspend fun getAlbumDetail(albumId: Int): Result<AlbumDetailDto> = try {
        val resp = api.getAlbumDetail(albumId)
        if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
        else Result.failure(Exception("Albüm bulunamadı"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getArtistDetail(artistId: Int): Result<ArtistDetailDto> = try {
        val resp = api.getArtistDetail(artistId)
        if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
        else Result.failure(Exception("Sanatçı bulunamadı"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getArtists(search: String? = null): Result<List<ArtistListItemDto>> = try {
        val resp = api.getArtists(search = search)
        if (resp.isSuccessful) Result.success(resp.body().orEmpty())
        else Result.failure(Exception("Sanatçılar alınamadı (${resp.code()})"))
    } catch (e: Exception) {
        Result.failure(e)
    }
}
