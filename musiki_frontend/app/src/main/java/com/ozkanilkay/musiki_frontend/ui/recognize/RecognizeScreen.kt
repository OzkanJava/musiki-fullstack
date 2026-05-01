package com.ozkanilkay.musiki_frontend.ui.recognize

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MusicNote
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.ozkanilkay.musiki_frontend.data.model.RecognizeSongResult
import com.ozkanilkay.musiki_frontend.ui.theme.Musiki

@Composable
fun RecognizeScreen(
    onOpenArtist: (Int) -> Unit,
    onOpenAlbum: (Int) -> Unit,
    viewModel: RecognizeViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val c = Musiki.colors

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) viewModel.startRecognition()
    }

    fun onStartClick() {
        val granted = ContextCompat.checkSelfPermission(
            context, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) viewModel.startRecognition()
        else permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
    }

    fun openSong(song: RecognizeSongResult) {
        if (song.album != null) onOpenAlbum(song.album.id)
        else onOpenArtist(song.artist.id)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(c.background)
            .padding(horizontal = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        when (val s = state) {
            is RecognizeState.Idle -> IdleContent(onStart = ::onStartClick)

            is RecognizeState.Recording -> RecordingContent(secondsLeft = s.secondsLeft)

            is RecognizeState.Recorded -> RecordedContent(
                isPlaying    = s.isPlaying,
                rmsDb        = s.rmsDb,
                onTogglePlay = viewModel::togglePlayback,
                onSend       = viewModel::sendToBackend,
                onReRecord   = viewModel::reRecord,
            )

            is RecognizeState.Uploading -> UploadingContent()

            is RecognizeState.Matched -> MatchedContent(
                topMatch     = s.topMatch,
                alternatives = s.alternatives,
                onOpenSong   = ::openSong,
                onOpenArtist = onOpenArtist,
                onRetry      = viewModel::reset,
            )

            is RecognizeState.NearMatches -> NearMatchesContent(
                guesses      = s.guesses,
                detail       = s.detail,
                onOpenSong   = ::openSong,
                onOpenArtist = onOpenArtist,
                onRetry      = viewModel::reset,
            )

            is RecognizeState.NoMatch -> NoMatchContent(
                detail  = s.detail,
                onRetry = viewModel::reset,
            )

            is RecognizeState.Error -> ErrorContent(
                message = s.message,
                onRetry = viewModel::reset,
            )
        }
    }
}

// ── Idle ──────────────────────────────────────────────────────────────────────

@Composable
private fun IdleContent(onStart: () -> Unit) {
    val c = Musiki.colors
    Box(
        modifier = Modifier
            .size(140.dp)
            .clip(CircleShape)
            .background(c.gray),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Default.Mic,
            contentDescription = null,
            tint = c.textSecondary,
            modifier = Modifier.size(56.dp),
        )
    }

    Spacer(Modifier.height(32.dp))

    Text(
        text = "Müzik Tanı",
        style = MaterialTheme.typography.headlineSmall,
        color = c.textPrimary,
        fontWeight = FontWeight.Bold,
    )
    Spacer(Modifier.height(8.dp))
    Text(
        text = "Etrafındaki müziği 13 saniye dinler\nve hangi şarkı olduğunu söyler.",
        style = MaterialTheme.typography.bodyMedium,
        color = c.textSecondary,
        textAlign = TextAlign.Center,
    )

    Spacer(Modifier.height(40.dp))

    Button(
        onClick = onStart,
        modifier = Modifier
            .fillMaxWidth()
            .height(52.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
    ) {
        Icon(Icons.Default.Mic, contentDescription = null, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(8.dp))
        Text("Dinlemeye Başla", style = MaterialTheme.typography.titleMedium)
    }
}

// ── Recording ─────────────────────────────────────────────────────────────────

@Composable
private fun RecordingContent(secondsLeft: Int) {
    val c = Musiki.colors
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val outerScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue  = 1.25f,
        animationSpec = infiniteRepeatable(
            animation  = tween(700, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "outerScale",
    )
    val innerScale by infiniteTransition.animateFloat(
        initialValue = 0.92f,
        targetValue  = 1f,
        animationSpec = infiniteRepeatable(
            animation  = tween(700, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "innerScale",
    )

    Box(contentAlignment = Alignment.Center) {
        Box(
            modifier = Modifier
                .size(160.dp)
                .scale(outerScale)
                .clip(CircleShape)
                .background(c.primary.copy(alpha = 0.25f)),
        )
        Box(
            modifier = Modifier
                .size(120.dp)
                .scale(innerScale)
                .clip(CircleShape)
                .background(c.primary),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = secondsLeft.toString(),
                style = MaterialTheme.typography.displaySmall,
                color = c.onPrimary,
                fontWeight = FontWeight.Bold,
            )
        }
    }

    Spacer(Modifier.height(32.dp))

    Text(
        text = "Dinliyor...",
        style = MaterialTheme.typography.titleLarge,
        color = c.textPrimary,
    )
    Spacer(Modifier.height(8.dp))
    Text(
        text = "Müziğin yakınında tut",
        style = MaterialTheme.typography.bodyMedium,
        color = c.textSecondary,
    )
}

// ── Recorded ──────────────────────────────────────────────────────────────────

@Composable
private fun RecordedContent(
    isPlaying: Boolean,
    rmsDb: Double,
    onTogglePlay: () -> Unit,
    onSend: () -> Unit,
    onReRecord: () -> Unit,
) {
    val c = Musiki.colors
    val isSilent = rmsDb < -50.0
    Box(
        modifier = Modifier
            .size(100.dp)
            .clip(CircleShape)
            .background(
                if (isSilent) c.error.copy(alpha = 0.15f)
                else c.primary.copy(alpha = 0.15f)
            ),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Default.Mic,
            contentDescription = null,
            tint = if (isSilent) c.error else c.primary,
            modifier = Modifier.size(48.dp),
        )
    }

    Spacer(Modifier.height(24.dp))

    Text(
        text = "Kayıt Tamamlandı",
        style = MaterialTheme.typography.headlineSmall,
        color = c.textPrimary,
        fontWeight = FontWeight.Bold,
    )
    Spacer(Modifier.height(6.dp))
    Text(
        text = if (isSilent) {
            "Ses seviyesi çok düşük — müziği yakınlaştırın veya tekrar kaydedin."
        } else {
            "Kaydı dinle, ardından tanıtmaya gönder."
        },
        style = MaterialTheme.typography.bodyMedium,
        color = if (isSilent) c.error else c.textSecondary,
        textAlign = TextAlign.Center,
    )

    Spacer(Modifier.height(32.dp))

    OutlinedButton(
        onClick = onTogglePlay,
        modifier = Modifier.fillMaxWidth().height(48.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, c.primary),
    ) {
        Icon(
            imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
            contentDescription = null,
            tint = c.primary,
            modifier = Modifier.size(20.dp),
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = if (isPlaying) "Durdur" else "Kaydı Dinle",
            color = c.primary,
            style = MaterialTheme.typography.titleSmall,
        )
    }

    Spacer(Modifier.height(12.dp))

    Button(
        onClick = onSend,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
    ) {
        Text("Tanı Et", style = MaterialTheme.typography.titleMedium)
    }

    Spacer(Modifier.height(8.dp))

    TextButton(onClick = onReRecord) {
        Icon(Icons.Default.Refresh, contentDescription = null, tint = c.textSecondary, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(4.dp))
        Text("Tekrar Kaydet", color = c.textSecondary, style = MaterialTheme.typography.bodyMedium)
    }
}

// ── Uploading ─────────────────────────────────────────────────────────────────

@Composable
private fun UploadingContent() {
    val c = Musiki.colors
    CircularProgressIndicator(
        modifier = Modifier.size(80.dp),
        color     = c.primary,
        strokeWidth = 6.dp,
    )

    Spacer(Modifier.height(32.dp))

    Text(
        text = "Analiz ediliyor...",
        style = MaterialTheme.typography.titleLarge,
        color = c.textPrimary,
    )
    Text(
        text = "Fingerprint veritabanında aranıyor",
        style = MaterialTheme.typography.bodyMedium,
        color = c.textSecondary,
    )
}

// ── Matched ───────────────────────────────────────────────────────────────────

@Composable
private fun MatchedContent(
    topMatch: RecognizeSongResult,
    alternatives: List<RecognizeSongResult>,
    onOpenSong: (RecognizeSongResult) -> Unit,
    onOpenArtist: (Int) -> Unit,
    onRetry: () -> Unit,
) {
    val c = Musiki.colors
    Box(
        modifier = Modifier
            .size(72.dp)
            .clip(CircleShape)
            .background(c.success.copy(alpha = 0.15f)),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Default.Check,
            contentDescription = null,
            tint = c.success,
            modifier = Modifier.size(40.dp),
        )
    }

    Spacer(Modifier.height(16.dp))

    Text(
        text = "Bulundu!",
        style = MaterialTheme.typography.headlineSmall,
        color = c.success,
        fontWeight = FontWeight.Bold,
    )

    Spacer(Modifier.height(20.dp))

    TopMatchCard(
        song = topMatch,
        onOpenSong = onOpenSong,
        onOpenArtist = onOpenArtist,
    )

    if (alternatives.isNotEmpty()) {
        Spacer(Modifier.height(20.dp))
        Text(
            text = "Diğer olası eşleşmeler",
            style = MaterialTheme.typography.titleSmall,
            color = c.textSecondary,
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(8.dp))
        alternatives.forEach { alt ->
            AlternativeCard(
                song = alt,
                onOpenSong = onOpenSong,
                onOpenArtist = onOpenArtist,
            )
            Spacer(Modifier.height(8.dp))
        }
    }

    Spacer(Modifier.height(20.dp))

    OutlinedButton(
        onClick = onRetry,
        modifier = Modifier.fillMaxWidth().height(48.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, c.primary),
    ) {
        Text("Tekrar Dene", color = c.primary)
    }
}

// ── NearMatches (REJECTED ama yakın tahminler) ────────────────────────────────

@Composable
private fun NearMatchesContent(
    guesses: List<RecognizeSongResult>,
    detail: String?,
    onOpenSong: (RecognizeSongResult) -> Unit,
    onOpenArtist: (Int) -> Unit,
    onRetry: () -> Unit,
) {
    val c = Musiki.colors
    Text(
        text = "Yakın tahminler",
        style = MaterialTheme.typography.headlineSmall,
        color = c.textPrimary,
        fontWeight = FontWeight.Bold,
    )

    Spacer(Modifier.height(8.dp))

    Text(
        text = detail ?: "Tam emin değilim, en yakın tahminler bunlar:",
        style = MaterialTheme.typography.bodyMedium,
        color = c.textSecondary,
        textAlign = TextAlign.Center,
    )

    Spacer(Modifier.height(20.dp))

    guesses.forEach { g ->
        AlternativeCard(
            song = g,
            onOpenSong = onOpenSong,
            onOpenArtist = onOpenArtist,
        )
        Spacer(Modifier.height(8.dp))
    }

    Spacer(Modifier.height(16.dp))

    OutlinedButton(
        onClick = onRetry,
        modifier = Modifier.fillMaxWidth().height(48.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, c.primary),
    ) {
        Text("Tekrar Dene", color = c.primary)
    }
}

// ── NoMatch ───────────────────────────────────────────────────────────────────

@Composable
private fun NoMatchContent(detail: String?, onRetry: () -> Unit) {
    val c = Musiki.colors
    Box(
        modifier = Modifier
            .size(96.dp)
            .clip(CircleShape)
            .background(c.error.copy(alpha = 0.15f)),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Default.Close,
            contentDescription = null,
            tint = c.error,
            modifier = Modifier.size(48.dp),
        )
    }

    Spacer(Modifier.height(24.dp))

    Text(
        text = "Eşleşme Bulunamadı",
        style = MaterialTheme.typography.headlineSmall,
        color = c.textPrimary,
        fontWeight = FontWeight.Bold,
    )
    Spacer(Modifier.height(8.dp))

    Text(
        text = detail ?: "Bu şarkı veritabanımızda yok\nveya ses çok gürültülüydü.",
        style = MaterialTheme.typography.bodyMedium,
        color = c.textSecondary,
        textAlign = TextAlign.Center,
    )

    Spacer(Modifier.height(24.dp))

    Button(
        onClick = onRetry,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
    ) {
        Text("Tekrar Dene", style = MaterialTheme.typography.titleMedium)
    }
}

// ── Error ─────────────────────────────────────────────────────────────────────

@Composable
private fun ErrorContent(message: String, onRetry: () -> Unit) {
    val c = Musiki.colors
    Icon(
        imageVector = Icons.Default.Close,
        contentDescription = null,
        tint = c.error,
        modifier = Modifier.size(64.dp),
    )

    Spacer(Modifier.height(16.dp))

    Text(
        text = "Hata Oluştu",
        style = MaterialTheme.typography.titleLarge,
        color = c.textPrimary,
        fontWeight = FontWeight.Bold,
    )
    Spacer(Modifier.height(8.dp))
    Text(
        text = message,
        style = MaterialTheme.typography.bodySmall,
        color = c.error,
        textAlign = TextAlign.Center,
    )

    Spacer(Modifier.height(24.dp))

    Button(
        onClick = onRetry,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(containerColor = c.primary),
    ) {
        Text("Tekrar Dene")
    }
}

// ── Reusable cards ────────────────────────────────────────────────────────────

@Composable
private fun TopMatchCard(
    song: RecognizeSongResult,
    onOpenSong: (RecognizeSongResult) -> Unit,
    onOpenArtist: (Int) -> Unit,
) {
    val c = Musiki.colors
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenSong(song) },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = c.darkGray),
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            CoverBox(coverUrl = song.cover_image, size = 72)
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = song.title,
                    style = MaterialTheme.typography.titleMedium,
                    color = c.textPrimary,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = song.artist.username,
                    style = MaterialTheme.typography.bodyMedium,
                    color = c.textSecondary,
                    modifier = Modifier.clickable { onOpenArtist(song.artist.id) },
                )
                if (song.album != null) {
                    Text(
                        text = song.album.title,
                        style = MaterialTheme.typography.bodySmall,
                        color = c.textDisabled,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun AlternativeCard(
    song: RecognizeSongResult,
    onOpenSong: (RecognizeSongResult) -> Unit,
    onOpenArtist: (Int) -> Unit,
) {
    val c = Musiki.colors
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onOpenSong(song) },
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = c.darkGray.copy(alpha = 0.6f)),
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            CoverBox(coverUrl = song.cover_image, size = 48)
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = song.title,
                    style = MaterialTheme.typography.bodyMedium,
                    color = c.textPrimary,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = song.artist.username,
                    style = MaterialTheme.typography.bodySmall,
                    color = c.textSecondary,
                    modifier = Modifier.clickable { onOpenArtist(song.artist.id) },
                )
            }
        }
    }
}

@Composable
private fun CoverBox(coverUrl: String?, size: Int) {
    val c = Musiki.colors
    if (!coverUrl.isNullOrBlank()) {
        AsyncImage(
            model = coverUrl,
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .size(size.dp)
                .clip(RoundedCornerShape(8.dp)),
        )
    } else {
        Box(
            modifier = Modifier
                .size(size.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(c.gray),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Default.MusicNote,
                contentDescription = null,
                tint = c.primary,
                modifier = Modifier.size((size * 0.45).dp),
            )
        }
    }
}
