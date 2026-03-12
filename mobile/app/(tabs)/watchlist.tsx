import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function WatchlistScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Watchlist</Text>
        <Text style={styles.subtitle}>Track your favorite stocks</Text>
      </View>
      <View style={styles.empty}>
        <Text style={styles.emptyText}>⭐{"\n"}No stocks in Watchlist</Text>
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#070B14' },
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#1A2332' },
  title: { fontSize: 24, fontWeight: '800', color: '#FFF', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#8899AA' },
  empty: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { color: '#4A5568', fontSize: 16, textAlign: 'center', lineHeight: 28 },
});
