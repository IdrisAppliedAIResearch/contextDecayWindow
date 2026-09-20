"""Unchanged registered scoring and analysis for fresh thinking-off responses."""
import sys
import score_confirmation
score_confirmation.P=score_confirmation.P.parent/'restart005'

if __name__=='__main__':
    if sys.argv[1]=='score':score_confirmation.main()
    elif sys.argv[1]=='resolve':
        import resolve_confirmation
        resolve_confirmation.main()
    elif sys.argv[1]=='analyze':
        import analyze_confirmation
        analyze_confirmation.main()
    else:raise ValueError('Expected score, resolve, or analyze')
