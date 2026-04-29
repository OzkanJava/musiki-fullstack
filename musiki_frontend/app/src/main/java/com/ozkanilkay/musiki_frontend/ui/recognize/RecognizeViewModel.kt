package com.ozkanilkay.musiki_frontend.ui.recognize

import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaPlayer
import android.media.MediaRecorder
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.model.RecognizeSongResult
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import javax.inject.Inject
import kotlin.math.sqrt

sealed class RecognizeState {
    object Idle : RecognizeState()
    data class Recording(val secondsLeft: Int) : RecognizeState()
    data class Recorded(val isPlaying: Boolean = false, val rmsDb: Double = 0.0) : RecognizeState()
    object Uploading : RecognizeState()
    data class Matched(val result: RecognizeSongResult) : RecognizeState()
    data class NoMatch(
        val reason: String? = null,
        val detail: String? = null,
        val candidate: RecognizeSongResult? = null,
        val totalHashes: Int? = null,
    ) : RecognizeState()
    data class Error(val message: String) : RecognizeState()
}

private const val SAMPLE_RATE    = 44100
private const val RECORD_SECONDS = 13

// Yerel sessizlik esigi: bu seviyenin altindaki kayitlar backende gonderilmez.
// -50 dBFS ~ mikrofon bias + bos odadan duyulan genel gurultu seviyesi.
// Gercek muzik varsa RMS genellikle -30dB civari olur.
private const val SILENCE_GATE_DB = -50.0

@HiltViewModel
class RecognizeViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val api: ApiService,
) : ViewModel() {

    private val _state = MutableStateFlow<RecognizeState>(RecognizeState.Idle)
    val state = _state.asStateFlow()

    // Recorded bytes held in memory until user confirms or re-records
    private var recordedWav: ByteArray? = null
    private var mediaPlayer: MediaPlayer? = null

    // ── Public actions ────────────────────────────────────────────────────────

    fun startRecognition() {
        viewModelScope.launch {
            // Recording on IO; countdown on Main
            val recordingDeferred = async(Dispatchers.IO) { recordAudio() }

            for (sec in RECORD_SECONDS downTo 1) {
                _state.value = RecognizeState.Recording(sec)
                delay(1000)
            }

            val pcmData = recordingDeferred.await()
            val rmsDb = computeRmsDb(pcmData)
            recordedWav = encodeWav(pcmData)
            _state.value = RecognizeState.Recorded(rmsDb = rmsDb)
        }
    }

    fun togglePlayback() {
        val wav = recordedWav ?: return
        val currentState = _state.value as? RecognizeState.Recorded ?: return

        if (currentState.isPlaying) {
            mediaPlayer?.pause()
            _state.value = RecognizeState.Recorded(isPlaying = false)
        } else {
            val tmpFile = File(context.cacheDir, "preview.wav")
            tmpFile.writeBytes(wav)

            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                setDataSource(tmpFile.absolutePath)
                prepare()
                start()
                setOnCompletionListener {
                    _state.value = RecognizeState.Recorded(isPlaying = false)
                }
            }
            _state.value = RecognizeState.Recorded(isPlaying = true)
        }
    }

    fun sendToBackend() {
        val wav = recordedWav ?: return
        val current = _state.value as? RecognizeState.Recorded
        stopPlayback()

        // Yerel sessizlik gate — cok dusuk sesli kayitlari sunucuya yollama
        if (current != null && current.rmsDb < SILENCE_GATE_DB) {
            _state.value = RecognizeState.Error(
                "Yetersiz ses — çevrenizde müzik çalıyor olmalı. Tekrar deneyin."
            )
            return
        }

        viewModelScope.launch {
            _state.value = RecognizeState.Uploading
            try {
                val part = MultipartBody.Part.createFormData(
                    name     = "audio",
                    filename = "recognition.wav",
                    body     = wav.toRequestBody("audio/wav".toMediaTypeOrNull()),
                )
                val resp = api.recognizeSong(part)
                if (resp.isSuccessful) {
                    val body = resp.body()!!
                    _state.value = if (body.song != null) {
                        RecognizeState.Matched(body.song)
                    } else {
                        RecognizeState.NoMatch(
                            reason      = body.reason,
                            detail      = body.detail,
                            candidate   = body.candidate,
                            totalHashes = body.total_hashes,
                        )
                    }
                } else {
                    _state.value = RecognizeState.Error("Sunucu hatası (${resp.code()})")
                }
            } catch (e: Exception) {
                _state.value = RecognizeState.Error("Bağlantı hatası: ${e.message}")
            }
        }
    }

    fun reRecord() {
        stopPlayback()
        recordedWav = null
        _state.value = RecognizeState.Idle
    }

    fun reset() {
        stopPlayback()
        recordedWav = null
        _state.value = RecognizeState.Idle
    }

    override fun onCleared() {
        stopPlayback()
        super.onCleared()
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    private fun stopPlayback() {
        mediaPlayer?.release()
        mediaPlayer = null
    }

    @SuppressLint("MissingPermission")
    private fun recordAudio(): ByteArray {
        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        val recorder = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize,
        )

        val totalSamples = SAMPLE_RATE * RECORD_SECONDS
        val samples = ShortArray(totalSamples)

        recorder.startRecording()
        var offset = 0
        while (offset < totalSamples) {
            val toRead = minOf(bufferSize / 2, totalSamples - offset)
            val read = recorder.read(samples, offset, toRead)
            if (read <= 0) break
            offset += read
        }
        recorder.stop()
        recorder.release()

        return ByteBuffer.allocate(samples.size * 2)
            .order(ByteOrder.LITTLE_ENDIAN)
            .also { buf -> samples.forEach(buf::putShort) }
            .array()
    }

    /**
     * PCM 16-bit little-endian ByteArray'in RMS seviyesini dBFS olarak doner.
     * Sessiz kayit -inf, 0dBFS (full-scale) 0.0 dondurur.
     */
    private fun computeRmsDb(pcm: ByteArray): Double {
        if (pcm.size < 2) return -120.0
        val sampleCount = pcm.size / 2
        var sumSquares = 0.0
        val buf = ByteBuffer.wrap(pcm).order(ByteOrder.LITTLE_ENDIAN)
        for (i in 0 until sampleCount) {
            val s = buf.short.toDouble() / 32768.0
            sumSquares += s * s
        }
        val rms = sqrt(sumSquares / sampleCount)
        if (rms < 1e-10) return -120.0
        return 20.0 * kotlin.math.log10(rms)
    }

    private fun encodeWav(pcm: ByteArray): ByteArray {
        val channels      = 1
        val bitsPerSample = 16
        val byteRate      = SAMPLE_RATE * channels * bitsPerSample / 8
        val blockAlign    = channels * bitsPerSample / 8

        return ByteBuffer.allocate(44 + pcm.size)
            .order(ByteOrder.LITTLE_ENDIAN)
            .apply {
                put("RIFF".toByteArray())
                putInt(36 + pcm.size)
                put("WAVE".toByteArray())
                put("fmt ".toByteArray())
                putInt(16)
                putShort(1)
                putShort(channels.toShort())
                putInt(SAMPLE_RATE)
                putInt(byteRate)
                putShort(blockAlign.toShort())
                putShort(bitsPerSample.toShort())
                put("data".toByteArray())
                putInt(pcm.size)
                put(pcm)
            }
            .array()
    }
}
