package com.ozkanilkay.musiki_frontend.ui.upload

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.AudioFile
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Image
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki
import com.ozkanilkay.musiki_frontend.ui.theme.musikiTextFieldColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UploadScreen(
    onBack: () -> Unit,
    viewModel: UploadViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val c = Musiki.colors

    val audioPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            val cursor = context.contentResolver.query(uri, null, null, null, null)
            val name = cursor?.use {
                val idx = it.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                it.moveToFirst()
                if (idx >= 0) it.getString(idx) else "audio.mp3"
            } ?: "audio.mp3"
            viewModel.setAudioFile(uri, name)
        }
    }

    val coverPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia()
    ) { uri: Uri? ->
        viewModel.setCoverImage(uri)
    }

    if (state.isSuccess) {
        UploadSuccessScreen(onUploadMore = { viewModel.resetSuccess() })
        return
    }

    Scaffold(
        containerColor = c.background,
        contentWindowInsets = WindowInsets(0),
        topBar = {
            TopAppBar(
                title = { Text("Şarkı Yükle", color = c.textPrimary) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Geri", tint = c.textPrimary)
                    }
                },
                windowInsets = WindowInsets(0),
                colors = TopAppBarDefaults.topAppBarColors(containerColor = c.background),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // ── Kapak Resmi Seçici ───────────────────────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(120.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .border(
                            width = 1.5.dp,
                            color = if (state.coverUri != null) c.secondary else c.outline,
                            shape = RoundedCornerShape(14.dp),
                        )
                        .background(c.surface)
                        .clickable {
                            coverPicker.launch(
                                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            )
                        },
                    contentAlignment = Alignment.Center,
                ) {
                    if (state.coverUri != null) {
                        AsyncImage(
                            model = state.coverUri,
                            contentDescription = "Kapak görseli",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxSize(),
                        )
                    } else {
                        Icon(
                            imageVector = Icons.Default.Image,
                            contentDescription = null,
                            tint = c.textSecondary,
                            modifier = Modifier.size(40.dp),
                        )
                    }
                }
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(
                        "Kapak Görseli",
                        style = MaterialTheme.typography.titleMedium,
                        color = c.textPrimary,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        if (state.coverUri != null) "Değiştirmek için dokun" else "Seçmek için dokun",
                        style = MaterialTheme.typography.bodySmall,
                        color = c.textSecondary,
                    )
                }
            }

            // ── Ses Dosyası Seçici ───────────────────────────────────────────
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(110.dp)
                    .border(
                        width = 1.5.dp,
                        color = if (state.selectedUri != null) c.primary else c.outline,
                        shape = RoundedCornerShape(14.dp),
                    )
                    .background(c.surface, RoundedCornerShape(14.dp))
                    .clickable { audioPicker.launch("audio/*") },
                contentAlignment = Alignment.Center,
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Icon(
                        imageVector = if (state.selectedUri != null) Icons.Default.AudioFile else Icons.Default.CloudUpload,
                        contentDescription = null,
                        tint = if (state.selectedUri != null) c.primary else c.textSecondary,
                        modifier = Modifier.size(32.dp),
                    )
                    Text(
                        text = state.selectedFileName ?: "Ses dosyası seç (MP3, WAV, FLAC)",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (state.selectedUri != null) c.textPrimary else c.textSecondary,
                    )
                }
            }

            // ── Başlık ───────────────────────────────────────────────────────
            OutlinedTextField(
                value = state.title,
                onValueChange = viewModel::setTitle,
                label = { Text("Şarkı başlığı") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = musikiTextFieldColors(),
            )

            // ── Tür Seçimi ───────────────────────────────────────────────────
            Text(
                text = "Tür",
                style = MaterialTheme.typography.labelMedium,
                color = c.textSecondary,
            )
            GenreSelector(
                selected = state.genre,
                onSelect = viewModel::setGenre,
            )

            if (state.genre == "other") {
                OutlinedTextField(
                    value = state.customGenre,
                    onValueChange = viewModel::setCustomGenre,
                    label = { Text("Tür adı") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = musikiTextFieldColors(),
                )
            }

            // ── Hata ─────────────────────────────────────────────────────────
            if (state.error != null) {
                Text(
                    text = state.error!!,
                    color = c.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            // ── Yükle Butonu (turuncu vurgu) ─────────────────────────────────
            val customOk = state.genre != "other" || state.customGenre.isNotBlank()
            Button(
                onClick = viewModel::upload,
                enabled = !state.isUploading && customOk,
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = c.secondary,
                    contentColor = c.onSecondary,
                ),
            ) {
                if (state.isUploading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = c.onSecondary,
                        strokeWidth = 2.dp,
                    )
                    Spacer(Modifier.width(10.dp))
                    Text("Yükleniyor...")
                } else {
                    Text("Yükle", style = MaterialTheme.typography.titleMedium)
                }
            }
        }
    }
}

@Composable
private fun GenreSelector(selected: String, onSelect: (String) -> Unit) {
    val c = Musiki.colors
    val rows = GENRE_OPTIONS.chunked(2)
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        rows.forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { (key, label) ->
                    val isSelected = selected == key
                    FilterChip(
                        selected = isSelected,
                        onClick = { onSelect(key) },
                        label = { Text(label) },
                        modifier = Modifier.weight(1f),
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = c.primary.copy(alpha = 0.2f),
                            selectedLabelColor = c.primary,
                            containerColor = c.surface,
                            labelColor = c.textSecondary,
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            enabled = true,
                            selected = isSelected,
                            selectedBorderColor = c.primary,
                            borderColor = c.outline,
                        ),
                    )
                }
                if (row.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

@Composable
private fun UploadSuccessScreen(onUploadMore: () -> Unit) {
    val c = Musiki.colors
    Box(
        modifier = Modifier.fillMaxSize().background(c.background),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Icon(
                imageVector = Icons.Default.CheckCircle,
                contentDescription = null,
                tint = c.success,
                modifier = Modifier.size(72.dp),
            )
            Text(
                text = "Şarkı Yüklendi!",
                style = MaterialTheme.typography.headlineSmall,
                color = c.textPrimary,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = "Fingerprint oluşturulurken şarkın kütüphanede görünecek.",
                style = MaterialTheme.typography.bodyMedium,
                color = c.textSecondary,
            )
            Button(
                onClick = onUploadMore,
                colors = ButtonDefaults.buttonColors(
                    containerColor = c.secondary,
                    contentColor = c.onSecondary,
                ),
            ) {
                Text("Başka Şarkı Yükle")
            }
        }
    }
}
