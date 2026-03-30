import React, { useState } from 'react';

function History() {
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [dateList, setDateList] = useState([]);
  const [openDetails, setOpenDetails] = useState({});

  const generateDateList = () => {
    if (!fromDate || !toDate) return;

    const start = new Date(fromDate);
    const end = new Date(toDate);
    const dates = [];

    while (start <= end) {
      dates.push(new Date(start));
      start.setDate(start.getDate() + 1);
    }

    setDateList(dates);
    setOpenDetails({});
  };

  const toggleDetails = (dateStr) => {
    setOpenDetails((prev) => ({
      ...prev,
      [dateStr]: !prev[dateStr],
    }));
  };

  const formatDate = (dateObj) => {
    const options = { day: 'numeric', month: 'long', year: 'numeric' };
    return dateObj.toLocaleDateString('en-GB', options);
  };

  return (
    <div style={{ padding: '20px', color: 'white', textAlign: 'center' }}>
      <h2>Detection History</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <label>
          From: 
          <input 
            type="date" 
            value={fromDate} 
            onChange={(e) => setFromDate(e.target.value)} 
            style={{ marginLeft: '10px', marginRight: '20px' }}
          />
        </label>

        <label>
          To: 
          <input 
            type="date" 
            value={toDate} 
            onChange={(e) => setToDate(e.target.value)} 
            style={{ marginLeft: '10px' }}
          />
        </label>

        <button 
          onClick={generateDateList}
          style={{ marginLeft: '20px', padding: '5px 10px' }}
        >
          Show History
        </button>
      </div>

      {dateList.length > 0 ? (
        <ul style={{ 
          listStyleType: 'none', 
          padding: 0, 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center',
          gap: '15px'
        }}>
          {dateList.map((dateObj) => {
            const dateStr = dateObj.toISOString().split('T')[0];
            return (
              <li 
                key={dateStr} 
                style={{ 
                  width: '100%', 
                  maxWidth: '400px', 
                  background: '#222', 
                  padding: '10px', 
                  borderRadius: '8px' 
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
                  <strong>{formatDate(dateObj)}</strong>
                  <button 
                    onClick={() => toggleDetails(dateStr)}
                    style={{ padding: '5px 10px' }}
                  >
                    {openDetails[dateStr] ? 'Hide Details' : 'Show Details'}
                  </button>
                </div>
                {openDetails[dateStr] && (
                  <div style={{ 
                    marginTop: '8px', 
                    background: '#333', 
                    padding: '10px', 
                    borderRadius: '5px', 
                    textAlign: 'left' 
                  }}>
                    <p><strong>Details for {formatDate(dateObj)}:</strong></p>
                    <ul style={{ paddingLeft: '20px' }}>
                      <li>Drone Type: Example Drone</li>
                      <li>Detections: 3</li>
                      <li>Average Confidence: 0.75</li>
                    </ul>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <p>No dates selected.</p>
      )}
    </div>
  );
}

export default History;
