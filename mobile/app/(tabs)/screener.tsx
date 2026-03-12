import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function ScreenerScreen() {
  const scans = [
    { id: 1, name: 'Opening Range Breakout', time: '15m', cat: 'Breakout', color: '#00D4FF' },
    { id: 2, name: 'RSI Bullish Divergence', time: '1h', cat: 'RSI', color: '#00FF88' },
    { id: 3, name: 'EMA 21/50 Crossover', time: 'Daily', cat: 'EMA', color: '#FFB800' },
    { id: 4, name: 'Volume Spike Near Support', time: '15m', cat: 'Volume', color: '#FF3B5C' },
    { id: 5, name: 'MACD Zero Line Cross', time: '1h', cat: 'MACD', color: '#00D4FF' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Screener</Text>
        <Text style={styles.subtitle}>Select a scan to find opportunities in real-time</Text>
      </View>
      
      <ScrollView contentContainerStyle={styles.scroll}>
        {scans.map(s => (
          <TouchableOpacity key={s.id} style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.scanName}>{s.name}</Text>
            </View>
            <View style={styles.badgeRow}>
              <View style={[styles.badge, { backgroundColor: s.color + '22', borderColor: s.color + '55' }]}>
                <Text style={[styles.badgeText, { color: s.color }]}>{s.time}</Text>
              </View>
              <View style={[styles.badge, { backgroundColor: '#1A2332' }]}>
                <Text style={[styles.badgeText, { color: '#8899AA' }]}>{s.cat}</Text>
              </View>
            </View>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#070B14' },
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#1A2332' },
  title: { fontSize: 24, fontWeight: '800', color: '#FFF', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#8899AA' },
  scroll: { padding: 16 },
  card: { backgroundColor: '#0D1421', padding: 16, borderRadius: 12, marginBottom: 12, borderWidth: 1, borderColor: '#1A2332' },
  cardHeader: { marginBottom: 12 },
  scanName: { fontSize: 16, fontWeight: '700', color: '#FFF' },
  badgeRow: { flexDirection: 'row', gap: 8 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, borderWidth: 1, borderColor: 'transparent' },
  badgeText: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase' },
});
