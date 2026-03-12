import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';

export default function HomeScreen() {
  const scanHits = [
    { symbol: 'RELIANCE', scan: 'Opening Range Breakout', ltp: 2954.30, chg: 1.2 },
    { symbol: 'HDFCBANK', scan: 'EMA 21 Crossover', ltp: 1450.80, chg: 0.8 },
    { symbol: 'TCS', scan: 'RSI Oversold', ltp: 3890.00, chg: -0.4 },
  ];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>BreakoutScan</Text>
            <View style={styles.statusRow}>
              <View style={styles.dot} />
              <Text style={styles.subtitle}>Market Open • NSE</Text>
            </View>
          </View>
          <View style={styles.avatar}><Text style={styles.avatarText}>A</Text></View>
        </View>

        {/* Stats Grid */}
        <View style={styles.grid}>
          {[
            { label: 'Scan Hits', val: '124', color: '#00D4FF' },
            { label: 'Watchlist', val: '12', color: '#00FF88' },
            { label: 'Alerts', val: '3', color: '#FFB800' },
            { label: 'Advances', val: '62%', color: '#00FF88' },
          ].map(s => (
            <View key={s.label} style={styles.card}>
              <Text style={[styles.cardVal, { color: s.color }]}>{s.val}</Text>
              <Text style={styles.cardLabel}>{s.label}</Text>
            </View>
          ))}
        </View>

        {/* Live Hits */}
        <Text style={styles.sectionTitle}>🎯 Live Scan Hits</Text>
        {scanHits.map(hit => (
          <TouchableOpacity key={hit.symbol} style={styles.row} onPress={() => router.push(`/chart/${hit.symbol}`)}>
            <View style={{ flex: 1 }}>
              <Text style={styles.symbol}>{hit.symbol}</Text>
              <Text style={styles.scanName}>{hit.scan}</Text>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={styles.ltp}>₹{hit.ltp.toFixed(2)}</Text>
              <Text style={[styles.chg, { color: hit.chg >= 0 ? '#00FF88' : '#FF3B5C' }]}>
                {hit.chg >= 0 ? '▲' : '▼'} {Math.abs(hit.chg)}%
              </Text>
            </View>
          </TouchableOpacity>
        ))}
        <TouchableOpacity style={styles.btn} onPress={() => router.push('/screener')}>
          <Text style={styles.btnText}>View All Scans →</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#070B14' },
  scroll: { padding: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  title: { fontSize: 24, fontWeight: '800', color: '#FFF' },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 4 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#00FF88' },
  subtitle: { color: '#8899AA', fontSize: 13, fontWeight: '500' },
  avatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#00D4FF', justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#000', fontWeight: '700', fontSize: 16 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 24 },
  card: { flex: 1, minWidth: '45%', backgroundColor: '#0D1421', padding: 16, borderRadius: 12, borderWidth: 1, borderColor: '#1A2332' },
  cardVal: { fontSize: 28, fontWeight: '800', marginBottom: 4 },
  cardLabel: { fontSize: 12, color: '#8899AA', textTransform: 'uppercase', letterSpacing: 0.5 },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#FFF', marginBottom: 12, marginTop: 8 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#0D1421', padding: 16, borderRadius: 12, marginBottom: 8, borderWidth: 1, borderColor: '#1A2332' },
  symbol: { fontSize: 16, fontWeight: '700', color: '#FFF', marginBottom: 4 },
  scanName: { fontSize: 12, color: '#8899AA' },
  ltp: { fontSize: 16, fontWeight: '600', color: '#FFF', marginBottom: 4 },
  chg: { fontSize: 13, fontWeight: '600' },
  btn: { backgroundColor: '#111A2B', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8, borderWidth: 1, borderColor: '#00D4FF33' },
  btnText: { color: '#00D4FF', fontWeight: '600', fontSize: 14 },
});
