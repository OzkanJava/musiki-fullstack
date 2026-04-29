package com.ozkanilkay.musiki_frontend.data.repository

import com.ozkanilkay.musiki_frontend.data.model.PlaylistAddItemRequest
import com.ozkanilkay.musiki_frontend.data.model.PlaylistCreateRequest
import com.ozkanilkay.musiki_frontend.data.model.PlaylistDetailDto
import com.ozkanilkay.musiki_frontend.data.model.PlaylistDto
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PlaylistRepository @Inject constructor(private val api: ApiService) {

    suspend fun getPlaylists(): Result<List<PlaylistDto>> = try {
        val resp = api.getPlaylists()
        if (resp.isSuccessful) Result.success(resp.body()?.results.orEmpty())
        else Result.failure(Exception("Playlistler alınamadı (${resp.code()})"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun createPlaylist(title: String, description: String = ""): Result<PlaylistDto> = try {
        val resp = api.createPlaylist(PlaylistCreateRequest(title, description))
        if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
        else Result.failure(Exception("Playlist oluşturulamadı"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun getDetail(playlistId: Int): Result<PlaylistDetailDto> = try {
        val resp = api.getPlaylistDetail(playlistId)
        if (resp.isSuccessful && resp.body() != null) Result.success(resp.body()!!)
        else Result.failure(Exception("Playlist bulunamadı"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun delete(playlistId: Int): Result<Unit> = try {
        val resp = api.deletePlaylist(playlistId)
        if (resp.isSuccessful) Result.success(Unit)
        else Result.failure(Exception("Silinemedi"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun addSong(playlistId: Int, songId: Int): Result<Unit> = try {
        val resp = api.addPlaylistItem(playlistId, PlaylistAddItemRequest(songId))
        if (resp.isSuccessful) Result.success(Unit)
        else Result.failure(Exception("Eklenemedi"))
    } catch (e: Exception) { Result.failure(e) }

    suspend fun removeItem(playlistId: Int, itemId: Int): Result<Unit> = try {
        val resp = api.removePlaylistItem(playlistId, itemId)
        if (resp.isSuccessful) Result.success(Unit)
        else Result.failure(Exception("Çıkarılamadı"))
    } catch (e: Exception) { Result.failure(e) }
}
