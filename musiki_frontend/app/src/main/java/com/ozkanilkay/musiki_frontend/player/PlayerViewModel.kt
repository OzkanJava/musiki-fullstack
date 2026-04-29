package com.ozkanilkay.musiki_frontend.player

import android.content.Context
import android.util.Log
import androidx.annotation.OptIn
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.datasource.DefaultDataSource
import androidx.media3.datasource.okhttp.OkHttpDataSource
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.exoplayer.source.DefaultMediaSourceFactory
import com.ozkanilkay.musiki_frontend.BuildConfig
import com.ozkanilkay.musiki_frontend.data.model.RecordListenRequest
import com.ozkanilkay.musiki_frontend.data.model.SongDto
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import javax.inject.Inject

enum class RepeatMode { OFF, ALL, ONE }

@OptIn(UnstableApi::class)
@HiltViewModel
class PlayerViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val okHttpClient: OkHttpClient,
    private val api: ApiService,
) : ViewModel() {

    val player: ExoPlayer = ExoPlayer.Builder(context)
        .setMediaSourceFactory(
            DefaultMediaSourceFactory(
                DefaultDataSource.Factory(context, OkHttpDataSource.Factory(okHttpClient))
            )
        )
        .build()

    private val _currentSong = MutableStateFlow<SongDto?>(null)
    val currentSong = _currentSong.asStateFlow()

    private val _isPlaying = MutableStateFlow(false)
    val isPlaying = _isPlaying.asStateFlow()

    private val _position = MutableStateFlow(0L)
    val position = _position.asStateFlow()

    private val _duration = MutableStateFlow(0L)
    val duration = _duration.asStateFlow()

    private val _queue = MutableStateFlow<List<SongDto>>(emptyList())
    val queue = _queue.asStateFlow()

    private val _queueIndex = MutableStateFlow(0)
    val queueIndex = _queueIndex.asStateFlow()

    private val _shuffleEnabled = MutableStateFlow(false)
    val shuffleEnabled = _shuffleEnabled.asStateFlow()

    private val _repeatMode = MutableStateFlow(RepeatMode.OFF)
    val repeatMode = _repeatMode.asStateFlow()

    // Dinleme süresi takibi
    private var listenStartMs = 0L
    private var accumulatedListenMs = 0L

    init {
        player.addListener(object : Player.Listener {
            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _isPlaying.value = isPlaying
                if (isPlaying) {
                    listenStartMs = System.currentTimeMillis()
                } else {
                    if (listenStartMs > 0) {
                        accumulatedListenMs += System.currentTimeMillis() - listenStartMs
                        listenStartMs = 0L
                    }
                }
            }

            override fun onMediaItemTransition(mediaItem: MediaItem?, reason: Int) {
                // ExoPlayer kendiliğinden sonraki şarkıya geçtiğinde (auto-advance veya next/prev)
                reportCurrentListen()
                val idx = player.currentMediaItemIndex
                val q = _queue.value
                if (idx in q.indices) {
                    _queueIndex.value = idx
                    _currentSong.value = q[idx]
                    _position.value = 0L
                    listenStartMs = if (player.isPlaying) System.currentTimeMillis() else 0L
                    accumulatedListenMs = 0L
                }
            }
        })

        // Position polling
        viewModelScope.launch {
            while (true) {
                if (player.isPlaying) {
                    _position.value = player.currentPosition
                    val d = player.duration
                    if (d > 0) _duration.value = d
                }
                delay(500)
            }
        }
    }

    fun toggleCurrentLike() {
        val song = _currentSong.value ?: return
        val newLiked = !song.is_liked
        _currentSong.value = song.copy(is_liked = newLiked)
        // kuyruktaki kopyayı da güncelle
        _queue.value = _queue.value.map { if (it.id == song.id) it.copy(is_liked = newLiked) else it }
        viewModelScope.launch {
            val result = runCatching {
                if (newLiked) api.likeSong(song.id) else api.unlikeSong(song.id)
            }
            val ok = result.getOrNull()?.isSuccessful == true
            if (!ok) {
                _currentSong.value = _currentSong.value?.copy(is_liked = !newLiked)
                _queue.value = _queue.value.map { if (it.id == song.id) it.copy(is_liked = !newLiked) else it }
            }
        }
    }

    /**
     * Yeni kuyruk yükleyip [startIndex] şarkısından oynatmaya başlar.
     * Album/playlist/home listelerinin "Çal" akışı için ana giriş noktasıdır.
     */
    fun playQueue(
        songs: List<SongDto>,
        startIndex: Int = 0,
        uriResolver: (SongDto) -> String = { "${BuildConfig.BASE_URL}api/music/songs/${it.id}/stream/" },
        forceMimeType: String? = MimeTypes.AUDIO_MPEG,
    ) {
        if (songs.isEmpty()) return
        reportCurrentListen()

        val safeIndex = startIndex.coerceIn(0, songs.lastIndex)
        _queue.value = songs
        _queueIndex.value = safeIndex

        val items = songs.map { song ->
            MediaItem.Builder()
                .setUri(uriResolver(song))
                .apply { if (forceMimeType != null) setMimeType(forceMimeType) }
                .setMediaId(song.id.toString())
                .build()
        }
        player.setMediaItems(items, safeIndex, 0L)
        player.prepare()
        player.play()

        _currentSong.value = songs[safeIndex]
        _position.value = 0L
        listenStartMs = System.currentTimeMillis()
        accumulatedListenMs = 0L
    }

    /** Kuyruktan belirli bir index'e atlar (Queue sheet'ten kullanılır). */
    fun seekToQueueIndex(index: Int) {
        if (index !in _queue.value.indices) return
        player.seekTo(index, 0L)
        player.play()
    }

    fun next() {
        if (player.hasNextMediaItem()) player.seekToNext()
    }

    fun previous() {
        // 3 sn'den sonraysa başa al; değilse gerçekten önceki parçaya git
        if (player.currentPosition > 3_000 || !player.hasPreviousMediaItem()) {
            player.seekTo(0L)
        } else {
            player.seekToPrevious()
        }
    }

    fun toggleShuffle() {
        val newVal = !_shuffleEnabled.value
        _shuffleEnabled.value = newVal
        player.shuffleModeEnabled = newVal
    }

    fun cycleRepeatMode() {
        val next = when (_repeatMode.value) {
            RepeatMode.OFF -> RepeatMode.ALL
            RepeatMode.ALL -> RepeatMode.ONE
            RepeatMode.ONE -> RepeatMode.OFF
        }
        _repeatMode.value = next
        player.repeatMode = when (next) {
            RepeatMode.OFF -> Player.REPEAT_MODE_OFF
            RepeatMode.ALL -> Player.REPEAT_MODE_ALL
            RepeatMode.ONE -> Player.REPEAT_MODE_ONE
        }
    }

    fun togglePlayPause() {
        if (player.isPlaying) player.pause() else player.play()
    }

    fun seekTo(positionMs: Long) {
        player.seekTo(positionMs)
        _position.value = positionMs
    }

    override fun onCleared() {
        reportCurrentListen()
        player.release()
        super.onCleared()
    }

    private fun reportCurrentListen() {
        val song = _currentSong.value ?: return

        if (listenStartMs > 0) {
            accumulatedListenMs += System.currentTimeMillis() - listenStartMs
            listenStartMs = 0L
        }

        val durationMs = accumulatedListenMs
        accumulatedListenMs = 0L

        if (durationMs < 2000) return

        viewModelScope.launch {
            try {
                api.recordListen(RecordListenRequest(song.id, durationMs))
            } catch (e: Exception) {
                Log.w("PlayerViewModel", "Listen kaydı gönderilemedi: ${e.message}")
            }
        }
    }
}
