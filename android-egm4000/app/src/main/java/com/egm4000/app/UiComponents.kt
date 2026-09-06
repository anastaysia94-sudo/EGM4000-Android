package com.egm4000.app

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.egm4000.app.data.EvidenceKind

@Composable
fun Page(title: String, kicker: String, subtitle: String, content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(kicker.uppercase(), color = Color(0xFFC79A55), style = MaterialTheme.typography.labelLarge)
        Text(title, color = Color(0xFF00F2FF), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
        Text(subtitle, color = Color(0xFFA8C0C8), style = MaterialTheme.typography.bodyMedium)
        content()
        Spacer(Modifier.height(64.dp))
    }
}

@Composable
fun Panel(title: String, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color(0xE60F1116)), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, color = Color(0xFF00D4C8), fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
fun ArtCard(drawable: Int, title: String, body: String) {
    Card(Modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFF0B1624))) {
        Box(Modifier.height(190.dp).fillMaxWidth()) {
            Image(painterResource(drawable), null, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color.Transparent, Color(0xEE050914)))))
            Column(Modifier.align(androidx.compose.ui.Alignment.BottomStart).padding(14.dp)) {
                Text(title, fontWeight = FontWeight.Black, color = Color.White)
                Text(body, color = Color(0xFFD9F8FF), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun Metric(value: String, label: String, modifier: Modifier = Modifier) {
    Card(modifier, colors = CardDefaults.cardColors(containerColor = Color(0xFF081827))) {
        Column(Modifier.padding(12.dp)) {
            Text(value, color = Color(0xFF00F2FF), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Black)
            Text(label, color = Color(0xFF9DB7C4), style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun EvidencePill(kind: EvidenceKind, confidence: Double) {
    val color = when (kind) {
        EvidenceKind.EXACT_TELEMETRY -> Color(0xFF38FFC6)
        EvidenceKind.USER_RECORDED, EvidenceKind.OBSERVED_EVIDENCE -> Color(0xFF00F2FF)
        EvidenceKind.ESTIMATE, EvidenceKind.DEVICE_SIGNAL -> Color(0xFFFFB84A)
        EvidenceKind.CORRELATION, EvidenceKind.HYPOTHESIS -> Color(0xFFB58CFF)
        EvidenceKind.UNKNOWN -> Color(0xFF8BA3AD)
    }
    Surface(color = color.copy(alpha = .12f), shape = RoundedCornerShape(100.dp), border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = .5f))) {
        Text("${kind.wire} • ${(confidence * 100).toInt()}%", Modifier.padding(horizontal = 9.dp, vertical = 4.dp), color = color, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
fun SafetyNotice() {
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF1B1720)), modifier = Modifier.fillMaxWidth()) {
        Text(
            "User-authorized evidence only. EGM4000 does not collect Fire Kirin credentials, read hidden server state, manipulate balances, bypass protections, guarantee profit, or claim certainty about random outcomes.",
            Modifier.padding(12.dp), color = Color(0xFFFFD8A8), style = MaterialTheme.typography.bodySmall
        )
    }
}
