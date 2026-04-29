package com.ozkanilkay.musiki_frontend.ui.upload

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ozkanilkay.musiki_frontend.data.remote.ApiService
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject

data class UploadUiState(
    val title: String = "",
    val genre: String = "rock",
    val customGenre: String = "",
    val selectedUri: Uri? = null,
    val selectedFileName: String? = null,
    val coverUri: Uri? = null,
    val isUploading: Boolean = false,
    val isSuccess: Boolean = false,
    val error: String? = null,
)

val GENRE_OPTIONS = listOf(
    "pop" to "Pop",
    "rock" to "Rock",
    "hip_hop" to "Hip Hop",
    "electronic" to "Electronic",
    "classical" to "Klasik",
    "jazz" to "Jazz",
    "folk" to "Folk",
    "other" to "Diğer",
)

@HiltViewModel
class UploadViewModel @Inject constructor(
    private val api: ApiService,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _uiState = MutableStateFlow(UploadUiState())
    val uiState = _uiState.asStateFlow()

    fun setTitle(value: String) = _uiState.update { it.copy(title = value, error = null) }
    fun setGenre(value: String) = _uiState.update { it.copy(genre = value, error = null) }
    fun setCustomGenre(value: String) = _uiState.update { it.copy(customGenre = value, error = null) }

    fun setAudioFile(uri: Uri, displayName: String) {
        _uiState.update { it.copy(selectedUri = uri, selectedFileName = displayName, error = null) }
    }

    fun setCoverImage(uri: Uri?) {
        _uiState.update { it.copy(coverUri = uri, error = null) }
    }

    fun upload() {
        val state = _uiState.value
        if (state.title.isBlank()) {
            _uiState.update { it.copy(error = "Şarkı başlığı boş olamaz") }
            return
        }
        if (state.selectedUri == null) {
            _uiState.update { it.copy(error = "Lütfen bir ses dosyası seç") }
            return
        }
        val genreToSend = if (state.genre == "other") state.customGenre.trim() else state.genre
        if (genreToSend.isBlank()) {
            _uiState.update { it.copy(error = "Lütfen bir tür adı gir") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isUploading = true, error = null) }
            try {
                val audioStream = context.contentResolver.openInputStream(state.selectedUri)
                    ?: throw Exception("Dosya açılamadı")
                val audioBytes = audioStream.use { it.readBytes() }

                val audioMime = context.contentResolver.getType(state.selectedUri) ?: "audio/mpeg"
                val fileName = state.selectedFileName ?: "audio.mp3"

                val audioBody = audioBytes.toRequestBody(audioMime.toMediaTypeOrNull())
                val audioPart = MultipartBody.Part.createFormData("audio_file", fileName, audioBody)

                val titleBody = state.title.trim().toRequestBody("text/plain".toMediaTypeOrNull())
                val genreBody = genreToSend.lowercase().toRequestBody("text/plain".toMediaTypeOrNull())

                val coverPart: MultipartBody.Part? = state.coverUri?.let { uri ->
                    val coverStream = context.contentResolver.openInputStream(uri)
                        ?: throw Exception("Kapak görseli açılamadı")
                    val coverBytes = coverStream.use { it.readBytes() }
                    val coverMime = context.contentResolver.getType(uri) ?: "image/jpeg"
                    val coverName = "cover.${coverMime.substringAfter('/', "jpg")}"
                    val coverBody = coverBytes.toRequestBody(coverMime.toMediaTypeOrNull())
                    MultipartBody.Part.createFormData("cover_image", coverName, coverBody)
                }

                val resp = api.uploadSong(
                    title = titleBody,
                    genre = genreBody,
                    audio_file = audioPart,
                    cover_image = coverPart,
                )

                if (resp.isSuccessful) {
                    _uiState.update { it.copy(isUploading = false, isSuccess = true) }
                } else {
                    val msg = resp.errorBody()?.string() ?: "Yükleme başarısız"
                    _uiState.update { it.copy(isUploading = false, error = msg) }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isUploading = false, error = "Hata: ${e.message}") }
            }
        }
    }

    fun resetSuccess() = _uiState.update { UploadUiState() }
}
