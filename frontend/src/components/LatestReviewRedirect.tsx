import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { fetchFiles } from '../api/client';

export default function LatestReviewRedirect() {
  const [target, setTarget] = useState<string | null>(null);

  useEffect(() => {
    fetchFiles()
      .then((files) => {
        const completed = files.filter((f) => f.status === 'completed');
        // Sort by upload_time descending, take the latest
        completed.sort(
          (a, b) => new Date(b.upload_time).getTime() - new Date(a.upload_time).getTime()
        );
        if (completed.length > 0) {
          setTarget(`/review/${completed[0].id}`);
        } else {
          setTarget('/');
        }
      })
      .catch(() => setTarget('/'));
  }, []);

  if (target) {
    return <Navigate to={target} replace />;
  }

  return (
    <div className="flex items-center justify-center py-32">
      <div className="w-8 h-8 border-2 border-[#533afd] border-t-transparent rounded-full animate-spin" />
    </div>
  );
}
