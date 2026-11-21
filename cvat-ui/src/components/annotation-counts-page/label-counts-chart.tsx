// SPDX-License-Identifier: MIT

import 'chart.js/auto';
import React from 'react';
import { Bar } from 'react-chartjs-2';

import type { LabelCount } from './annotation-counts-page';

const BAR_HEIGHT_PX = 22;
const DEFAULT_COLOR = '#1890ff';

interface Props {
    labels: LabelCount[];
}

function LabelCountsChart({ labels }: Readonly<Props>): JSX.Element {
    const data = {
        labels: labels.map((label) => label.name),
        datasets: [{
            label: 'Annotations',
            data: labels.map((label) => label.count),
            backgroundColor: labels.map((label) => label.color || DEFAULT_COLOR),
        }],
    };

    return (
        <div className='cvat-annotation-counts-chart' style={{ height: Math.max(200, labels.length * BAR_HEIGHT_PX) }}>
            <Bar
                data={data}
                options={{
                    indexAxis: 'y',
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
                }}
            />
        </div>
    );
}

export default React.memo(LabelCountsChart);
